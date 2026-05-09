import json
from collections import Counter

import httpx

from config import settings


SKILLS_QUESTIONS = [
    ("skills_q1", "Are the candidate's claimed skills credible?"),
    ("skills_q2", "Are the skills supported by actual work and research?"),
    ("skills_q3", "Which skills are central strengths, and which appear overstated?"),
    ("skills_q4", "How relevant are the candidate's evidenced skills to the target role?"),
]


def _safe_field(item: dict, key: str) -> dict:
    v = item.get(key, {})
    if isinstance(v, dict):
        return v
    return {"value": "missing", "status": "missing", "evidence": ""}


def _norm_text(value: str) -> str:
    return " ".join((value or "").strip().lower().split())


def _extract_terms_from_text(value: str) -> set[str]:
    text = _norm_text(value)
    if not text:
        return set()
    tokens = {t for t in text.replace("/", " ").replace(",", " ").split() if len(t) > 2}
    return tokens


def compute_skills_facts(parsed_payload: dict) -> dict:
    skills = parsed_payload.get("skills", []) if isinstance(parsed_payload, dict) else []
    experience = parsed_payload.get("experience", []) if isinstance(parsed_payload, dict) else []
    publications = parsed_payload.get("publications", []) if isinstance(parsed_payload, dict) else []
    education = parsed_payload.get("education", []) if isinstance(parsed_payload, dict) else []

    profile_terms = set()

    for e in experience:
        for key in ["job_title", "organization", "description"]:
            profile_terms.update(_extract_terms_from_text(_safe_field(e, key).get("value", "")))

    for p in publications:
        for key in ["title", "venue", "pub_type"]:
            profile_terms.update(_extract_terms_from_text(_safe_field(p, key).get("value", "")))

    for e in education:
        for key in ["degree_title", "specialization"]:
            profile_terms.update(_extract_terms_from_text(_safe_field(e, key).get("value", "")))

    rows = []
    status_counter = Counter()
    for idx, s in enumerate(skills):
        if not isinstance(s, dict):
            continue
        name = str(s.get("value", "missing"))
        if not name or name.lower() in {"missing", "unclear"}:
            status_counter["unsupported"] += 1
            rows.append(
                {
                    "index": idx,
                    "skill": name or "missing",
                    "claim_status": s.get("status", "missing"),
                    "evidence_strength": "unsupported",
                    "evidence_sources": [],
                    "evidence_snippet": s.get("evidence", ""),
                }
            )
            continue

        skill_terms = _extract_terms_from_text(name)
        overlap = bool(skill_terms & profile_terms)
        has_snippet = bool(str(s.get("evidence", "")).strip())

        if overlap and has_snippet:
            strength = "strongly_evidenced"
        elif overlap or has_snippet:
            strength = "partially_evidenced"
        else:
            strength = "weakly_evidenced"

        if strength == "strongly_evidenced":
            status_counter["strongly_evidenced"] += 1
        elif strength == "partially_evidenced":
            status_counter["partially_evidenced"] += 1
        elif strength == "weakly_evidenced":
            status_counter["weakly_evidenced"] += 1
        else:
            status_counter["unsupported"] += 1

        sources = []
        if overlap:
            sources.append("profile_overlap")
        if has_snippet:
            sources.append("claimed_evidence")

        rows.append(
            {
                "index": idx,
                "skill": name,
                "claim_status": s.get("status", "present"),
                "evidence_strength": strength,
                "evidence_sources": sources,
                "evidence_snippet": s.get("evidence", ""),
            }
        )

    total = len(rows)
    coverage = round(
        ((status_counter["strongly_evidenced"] + status_counter["partially_evidenced"]) / total),
        2,
    ) if total else 0.0

    top_strengths = [r["skill"] for r in rows if r["evidence_strength"] == "strongly_evidenced"][:8]
    weak_or_overstated = [r["skill"] for r in rows if r["evidence_strength"] in {"weakly_evidenced", "unsupported"}][:8]

    return {
        "skills_count": total,
        "skills_table": rows,
        "evidence_summary": {
            "strongly_evidenced": status_counter["strongly_evidenced"],
            "partially_evidenced": status_counter["partially_evidenced"],
            "weakly_evidenced": status_counter["weakly_evidenced"],
            "unsupported": status_counter["unsupported"],
            "coverage_ratio": coverage,
        },
        "top_strengths": top_strengths,
        "potentially_overstated": weak_or_overstated,
    }


def _extract_json(raw_text: str) -> dict:
    text = raw_text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in skills analysis response")
    return json.loads(text[start : end + 1])


def _build_skills_prompt(facts: dict) -> tuple[str, str]:
    sys = (
        "You are TALASH Skills Analyst. Answer only using provided skills facts. "
        "Never hallucinate. Return strict JSON only."
    )
    qlist = [{"question_id": qid, "question": q} for qid, q in SKILLS_QUESTIONS]
    usr = (
        "Given the skills facts and questions below, produce JSON with keys: "
        "answers (array), overall_skills_assessment (object).\n"
        "Each answer item must have: question_id, question, answer, status(answered|insufficient_data), confidence(0-1), evidence_fields(array).\n"
        "overall_skills_assessment must have: strength(weak|moderate|strong), summary, confidence(0-1).\n"
        f"FACTS:\n{json.dumps(facts, ensure_ascii=True)}\n"
        f"QUESTIONS:\n{json.dumps(qlist, ensure_ascii=True)}"
    )
    return sys, usr


async def run_skills_llm_analysis(facts: dict, model_name: str) -> dict:
    if not settings.openrouter_api_key:
        raise RuntimeError("OPENROUTER_API_KEY missing")
    system_prompt, user_prompt = _build_skills_prompt(facts)
    payload = {
        "model": model_name,
        "temperature": 0.1,
        "top_p": 0.9,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-Title": "TALASH Skills Analyzer",
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{settings.openrouter_base_url}/chat/completions",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

    content = data["choices"][0]["message"]["content"]
    result = _extract_json(content)
    if "answers" not in result:
        raise ValueError("Skills analysis response missing 'answers'")
    if "overall_skills_assessment" not in result:
        raise ValueError("Skills analysis response missing 'overall_skills_assessment'")
    return result
