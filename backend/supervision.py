import json
import re

import httpx

from config import settings


SUPERVISION_QUESTIONS = [
    ("sup_q1", "How substantial is the candidate's supervision experience overall?"),
    ("sup_q2", "Are the student names, levels, and roles clear and complete?"),
    ("sup_q3", "Does the supervision profile show sustained mentoring activity?"),
    ("sup_q4", "Are graduation years or completion periods reasonably captured?"),
    ("sup_q5", "Does the profile indicate academic leadership or advisory responsibility?"),
    ("sup_q6", "Overall, how strong is the supervision profile?"),
]


def _safe_field(item: dict, key: str) -> dict:
    v = item.get(key, {})
    if isinstance(v, dict):
        return v
    return {"value": "missing", "status": "missing", "evidence": ""}


def _extract_year(value: str) -> int | None:
    m = re.search(r"(19|20)\d{2}", str(value or ""))
    if not m:
        return None
    return int(m.group(0))


def compute_supervision_facts(parsed_payload: dict) -> dict:
    supervision = parsed_payload.get("supervision", []) if isinstance(parsed_payload, dict) else []

    rows = []
    for idx, item in enumerate(supervision):
        rows.append(
            {
                "index": idx,
                "student_name": _safe_field(item, "student_name").get("value", "missing"),
                "level": _safe_field(item, "level").get("value", "missing"),
                "role": _safe_field(item, "role").get("value", "missing"),
                "graduation_year": _safe_field(item, "graduation_year").get("value", "missing"),
                "year_sort": _extract_year(_safe_field(item, "graduation_year").get("value", "")),
                "status_flags": [
                    k
                    for k in ["student_name", "level", "role", "graduation_year"]
                    if _safe_field(item, k).get("status") != "present"
                ],
            }
        )

    rows_sorted = sorted(rows, key=lambda x: x.get("year_sort") or 0, reverse=True)

    role_counter = {}
    for row in rows_sorted:
        role = row.get("role", "missing")
        role_counter[role] = role_counter.get(role, 0) + 1

    return {
        "supervision_count": len(rows_sorted),
        "supervision_timeline": rows_sorted,
        "role_distribution": role_counter,
        "summary": {
            "has_supervision": len(rows_sorted) > 0,
            "has_multiple_students": len(rows_sorted) > 1,
            "unique_students": len({r.get("student_name") for r in rows_sorted if r.get("student_name")}),
        },
    }


def _extract_json(raw_text: str) -> dict:
    text = raw_text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in supervision analysis response")
    return json.loads(text[start : end + 1])


def _build_supervision_prompt(facts: dict) -> tuple[str, str]:
    sys = (
        "You are TALASH Supervision Analyst. Answer only using provided facts. "
        "Never hallucinate. Return strict JSON only."
    )
    qlist = [{"question_id": qid, "question": q} for qid, q in SUPERVISION_QUESTIONS]
    usr = (
        "Given the supervision facts and questions below, produce JSON with keys: "
        "answers (array), overall_supervision_assessment (object).\n"
        "Each answer item must have: question_id, question, answer, status(answered|insufficient_data), confidence(0-1), evidence_fields(array).\n"
        "overall_supervision_assessment must have: strength(weak|moderate|strong), summary, confidence(0-1).\n"
        f"FACTS:\n{json.dumps(facts, ensure_ascii=True)}\n"
        f"QUESTIONS:\n{json.dumps(qlist, ensure_ascii=True)}"
    )
    return sys, usr


async def run_supervision_llm_analysis(facts: dict, model_name: str) -> dict:
    if not settings.openrouter_api_key:
        raise RuntimeError("OPENROUTER_API_KEY missing")
    system_prompt, user_prompt = _build_supervision_prompt(facts)
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
        "X-Title": "TALASH Supervision Analyzer",
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
        raise ValueError("Supervision analysis response missing 'answers'")
    if "overall_supervision_assessment" not in result:
        raise ValueError("Supervision analysis response missing 'overall_supervision_assessment'")
    return result
