import datetime as dt
import json
import re

import httpx

from backend.config import settings


EXPERIENCE_QUESTIONS = [
    ("exp_q1", "Is the candidate's career timeline internally consistent?"),
    ("exp_q2", "Are there overlaps between education and employment, and are they reasonable?"),
    ("exp_q3", "Are there overlaps between multiple jobs, and are they legitimate?"),
    ("exp_q4", "Are there unexplained employment gaps?"),
    ("exp_q5", "Are professional gaps justified by productive activities where evidence exists?"),
    ("exp_q6", "Does the profile show career continuity, progression, and professional maturity?"),
]


def _safe_field(item: dict, key: str) -> dict:
    v = item.get(key, {})
    if isinstance(v, dict):
        return v
    return {"value": "missing", "status": "missing", "evidence": ""}


def _parse_month_year(value: str) -> tuple[int, int] | None:
    text = (value or "").strip()
    if not text or text.lower() in {"missing", "unclear"}:
        return None
    lower = text.lower()
    if lower in {"present", "current", "ongoing"}:
        now = dt.datetime.utcnow()
        return now.year, now.month

    m = re.search(r"(19|20)\d{2}", text)
    if not m:
        return None
    year = int(m.group(0))

    month_map = {
        "jan": 1,
        "feb": 2,
        "mar": 3,
        "apr": 4,
        "may": 5,
        "jun": 6,
        "jul": 7,
        "aug": 8,
        "sep": 9,
        "oct": 10,
        "nov": 11,
        "dec": 12,
    }
    month = 6
    for k, v in month_map.items():
        if k in lower:
            month = v
            break
    return year, month


def _months_between(start: tuple[int, int], end: tuple[int, int]) -> int:
    return (end[0] - start[0]) * 12 + (end[1] - start[1])


def _normalize_rank(job_title: str) -> int:
    t = (job_title or "").lower()
    if "intern" in t:
        return 1
    if "assistant" in t:
        return 2
    if "lecturer" in t:
        return 3
    if "associate" in t:
        return 4
    if "manager" in t or "lead" in t:
        return 5
    if "director" in t or "head" in t or "professor" in t:
        return 6
    return 3


def compute_experience_facts(parsed_payload: dict) -> dict:
    experience = parsed_payload.get("experience", []) if isinstance(parsed_payload, dict) else []
    education = parsed_payload.get("education", []) if isinstance(parsed_payload, dict) else []

    exp_rows = []
    for idx, e in enumerate(experience):
        title = _safe_field(e, "job_title").get("value", "missing")
        org = _safe_field(e, "organization").get("value", "missing")
        st = _safe_field(e, "start_date").get("value", "missing")
        ed = _safe_field(e, "end_date").get("value", "missing")
        is_current = _safe_field(e, "is_current").get("value", "unclear")
        st_parsed = _parse_month_year(st)
        ed_parsed = _parse_month_year(ed)

        duration_months = None
        if st_parsed and ed_parsed:
            dm = _months_between(st_parsed, ed_parsed)
            duration_months = dm if dm >= 0 else None

        exp_rows.append(
            {
                "index": idx,
                "job_title": title,
                "organization": org,
                "start_date": st,
                "end_date": ed,
                "is_current": is_current,
                "start_parsed": st_parsed,
                "end_parsed": ed_parsed,
                "duration_months": duration_months,
                "rank_score": _normalize_rank(title),
            }
        )

    exp_rows = sorted(
        exp_rows,
        key=lambda x: (x.get("start_parsed") or (9999, 12), x.get("end_parsed") or (9999, 12)),
    )

    job_overlaps = []
    gaps = []
    for i in range(len(exp_rows) - 1):
        a = exp_rows[i]
        b = exp_rows[i + 1]
        if a["end_parsed"] and b["start_parsed"]:
            diff = _months_between(a["end_parsed"], b["start_parsed"])
            if diff < 0:
                job_overlaps.append(
                    {
                        "job_a": a["job_title"],
                        "job_b": b["job_title"],
                        "overlap_months": abs(diff),
                        "note": "Concurrent roles detected",
                    }
                )
            elif diff > 2:
                gaps.append(
                    {
                        "after_job": a["job_title"],
                        "before_job": b["job_title"],
                        "gap_months": diff,
                    }
                )

    edu_ranges = []
    for e in education:
        s = _safe_field(e, "start_year").get("value", "missing")
        en = _safe_field(e, "end_year").get("value", "missing")
        s_parsed = _parse_month_year(str(s))
        e_parsed = _parse_month_year(str(en))
        if s_parsed and e_parsed:
            edu_ranges.append(
                {
                    "degree": _safe_field(e, "degree_title").get("value", "missing"),
                    "start": s_parsed,
                    "end": e_parsed,
                }
            )

    edu_job_overlaps = []
    for job in exp_rows:
        if not (job["start_parsed"] and job["end_parsed"]):
            continue
        for edu in edu_ranges:
            if not (job["end_parsed"] < edu["start"] or job["start_parsed"] > edu["end"]):
                ov = min(
                    _months_between(edu["start"], job["end_parsed"]),
                    _months_between(job["start_parsed"], edu["end"]),
                )
                if ov >= 0:
                    edu_job_overlaps.append(
                        {
                            "job_title": job["job_title"],
                            "degree": edu["degree"],
                            "overlap_detected": True,
                            "note": "Could be valid if part-time/assistantship",
                        }
                    )

    continuity = len(gaps) == 0
    progression_trend = "stable"
    if len(exp_rows) >= 2:
        rank_delta = exp_rows[-1]["rank_score"] - exp_rows[0]["rank_score"]
        if rank_delta > 0:
            progression_trend = "upward"
        elif rank_delta < 0:
            progression_trend = "downward"

    return {
        "experience_records_count": len(exp_rows),
        "experience_timeline": exp_rows,
        "job_overlaps": job_overlaps,
        "education_job_overlaps": edu_job_overlaps,
        "professional_gaps": gaps,
        "continuity": {
            "is_continuous": continuity,
            "progression_trend": progression_trend,
        },
    }


def _extract_json(raw_text: str) -> dict:
    text = raw_text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in experience analysis response")
    return json.loads(text[start : end + 1])


def _build_experience_prompt(facts: dict) -> tuple[str, str]:
    sys = (
        "You are TALASH Experience Analyst. Answer only using provided experience facts. "
        "Never hallucinate. Return strict JSON only."
    )
    qlist = [{"question_id": qid, "question": q} for qid, q in EXPERIENCE_QUESTIONS]
    usr = (
        "Given the experience facts and questions below, produce JSON with keys: "
        "answers (array), overall_experience_assessment (object).\n"
        "Each answer item must have: question_id, question, answer, status(answered|insufficient_data), confidence(0-1), evidence_fields(array).\n"
        "overall_experience_assessment must have: strength(weak|moderate|strong), summary, confidence(0-1).\n"
        f"FACTS:\n{json.dumps(facts, ensure_ascii=True)}\n"
        f"QUESTIONS:\n{json.dumps(qlist, ensure_ascii=True)}"
    )
    return sys, usr


async def run_experience_llm_analysis(facts: dict, model_name: str) -> dict:
    if not settings.openrouter_api_key:
        raise RuntimeError("OPENROUTER_API_KEY missing")
    system_prompt, user_prompt = _build_experience_prompt(facts)
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
        "X-Title": "TALASH Experience Analyzer",
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
        raise ValueError("Experience analysis response missing 'answers'")
    if "overall_experience_assessment" not in result:
        raise ValueError("Experience analysis response missing 'overall_experience_assessment'")
    return result
