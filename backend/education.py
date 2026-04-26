import datetime as dt
import json
import re

import httpx

from backend.config import settings


EDU_QUESTIONS = [
    ("edu_q1", "Is the candidate's early academic performance stable across stages?"),
    ("edu_q2", "What are the candidate's UG/PG marks or CGPA after normalization?"),
    ("edu_q3", "What is the candidate's actual degree progression path?"),
    ("edu_q4", "Are degree, institution, score, and timeline records complete and consistent?"),
    ("edu_q5", "How strong is institutional quality evidence, and where is ranking unavailable?"),
    ("edu_q6", "Does the profile show coherent educational progression and specialization consistency?"),
    ("edu_q7", "Are there educational gaps between stages, and what are their durations?"),
    ("edu_q8", "Are educational gaps justified by professional experience or productive activity?"),
    ("edu_q9", "Overall, how strong is the candidate's educational profile?"),
]


def _safe_field(item: dict, key: str) -> dict:
    v = item.get(key, {})
    if isinstance(v, dict):
        return v
    return {"value": "missing", "status": "missing", "evidence": ""}


def _to_float(value: str) -> float | None:
    if not value:
        return None
    m = re.search(r"\d+(?:\.\d+)?", value)
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None


def _norm_score(score_value: str, score_type: str) -> float | None:
    n = _to_float(score_value)
    if n is None:
        return None
    st = (score_type or "").lower().strip()
    if st == "percentage":
        return round(max(0.0, min(100.0, n)), 2)
    if st == "cgpa":
        base = 4.0 if n <= 4.0 else 5.0
        return round((n / base) * 100.0, 2)
    if st == "grade":
        return None
    if st == "division":
        return None
    return None


def _stage_order(level: str) -> int:
    l = (level or "").upper()
    mapping = {
        "SSE": 1,
        "SSC": 1,
        "HSSC": 2,
        "UG": 3,
        "BS": 3,
        "BSC": 3,
        "PG": 4,
        "MS": 5,
        "MPHIL": 6,
        "PHD": 7,
    }
    return mapping.get(l, 99)


def _extract_year(item: dict, key: str) -> int | None:
    field = _safe_field(item, key)
    if field.get("status") != "present":
        return None
    n = _to_float(str(field.get("value", "")))
    if n is None:
        return None
    year = int(n)
    if 1900 <= year <= 2100:
        return year
    return None


def compute_education_facts(parsed_payload: dict) -> dict:
    education = parsed_payload.get("education", []) if isinstance(parsed_payload, dict) else []
    experience = parsed_payload.get("experience", []) if isinstance(parsed_payload, dict) else []

    timeline = []
    for idx, item in enumerate(education):
        level = _safe_field(item, "level")
        degree = _safe_field(item, "degree_title")
        spec = _safe_field(item, "specialization")
        inst = _safe_field(item, "institution")
        board = _safe_field(item, "board_university")
        sy = _safe_field(item, "start_year")
        ey = _safe_field(item, "end_year")
        sv = _safe_field(item, "score_value")
        st = _safe_field(item, "score_type")

        normalized = _norm_score(str(sv.get("value", "")), str(st.get("value", "")))
        flags = []
        if inst.get("status") != "present" and board.get("status") != "present":
            flags.append("institution_missing")
        if sy.get("status") != "present" and ey.get("status") != "present":
            flags.append("timeline_missing")

        timeline.append(
            {
                "index": idx,
                "level": str(level.get("value", "missing")),
                "degree_title": str(degree.get("value", "missing")),
                "specialization": str(spec.get("value", "missing")),
                "institution": str(inst.get("value", "missing")),
                "board_university": str(board.get("value", "missing")),
                "start_year": str(sy.get("value", "missing")),
                "end_year": str(ey.get("value", "missing")),
                "score_raw": str(sv.get("value", "missing")),
                "score_type": str(st.get("value", "missing")).lower(),
                "score_normalized_100": normalized,
                "status_flags": flags,
            }
        )

    timeline_sorted = sorted(timeline, key=lambda x: (_stage_order(x.get("level", "")), x.get("end_year", "9999")))

    highest = None
    if timeline_sorted:
        highest = max(timeline_sorted, key=lambda x: _stage_order(x.get("level", "")))

    sequence = [x.get("level", "missing") for x in timeline_sorted]
    is_coherent = sequence == sorted(sequence, key=_stage_order)

    gaps = []
    for i in range(len(timeline_sorted) - 1):
        cur = timeline_sorted[i]
        nxt = timeline_sorted[i + 1]
        cur_end = _extract_year(
            {
                "end_year": {"value": cur.get("end_year", "missing"), "status": "present" if cur.get("end_year") != "missing" else "missing"}
            },
            "end_year",
        )
        nxt_start = _extract_year(
            {
                "start_year": {
                    "value": nxt.get("start_year", "missing"),
                    "status": "present" if nxt.get("start_year") != "missing" else "missing",
                }
            },
            "start_year",
        )
        if cur_end is not None and nxt_start is not None and nxt_start > cur_end:
            gap = round(float(nxt_start - cur_end), 2)
            gaps.append(
                {
                    "from_stage": cur.get("level", "unknown"),
                    "to_stage": nxt.get("level", "unknown"),
                    "gap_years": gap,
                    "classification": "major" if gap >= 2 else "minor",
                    "justified_by_experience": False,
                }
            )

    # deterministic justification check: any experience date range overlapping gap years
    for gap in gaps:
        f = gap.get("from_stage")
        t = gap.get("to_stage")
        from_rec = next((x for x in timeline_sorted if x.get("level") == f), None)
        to_rec = next((x for x in timeline_sorted if x.get("level") == t), None)
        if not from_rec or not to_rec:
            continue
        from_end = _to_float(str(from_rec.get("end_year", "")))
        to_start = _to_float(str(to_rec.get("start_year", "")))
        if from_end is None or to_start is None:
            continue
        justified = False
        for e in experience:
            s = _safe_field(e, "start_date").get("value", "")
            ed = _safe_field(e, "end_date").get("value", "")
            s_y = _to_float(str(s))
            e_y = _to_float(str(ed))
            if s_y is None:
                continue
            if e_y is None:
                e_y = float(dt.datetime.utcnow().year)
            if not (e_y < from_end or s_y > to_start):
                justified = True
                break
        gap["justified_by_experience"] = justified

    missing_paths = []
    unclear_paths = []
    for i, item in enumerate(education):
        for k, v in item.items():
            if isinstance(v, dict):
                s = v.get("status")
                if s == "missing":
                    missing_paths.append(f"education[{i}].{k}")
                if s == "unclear":
                    unclear_paths.append(f"education[{i}].{k}")

    return {
        "highest_qualification": {
            "level": highest.get("level", "missing") if highest else "missing",
            "degree_title": highest.get("degree_title", "missing") if highest else "missing",
            "institution": highest.get("institution", "missing") if highest else "missing",
            "end_year": highest.get("end_year", "missing") if highest else "missing",
        },
        "education_records_count": len(timeline_sorted),
        "education_timeline": timeline_sorted,
        "score_summary": {
            "sse_hssc_present": any(x.get("level", "").upper() in {"SSE", "SSC", "HSSC"} for x in timeline_sorted),
            "ug_present": any(_stage_order(x.get("level", "")) == 3 for x in timeline_sorted),
            "pg_present": any(_stage_order(x.get("level", "")) >= 4 for x in timeline_sorted),
            "normalized_scores_available": sum(1 for x in timeline_sorted if x.get("score_normalized_100") is not None),
        },
        "progression": {
            "sequence": sequence,
            "is_coherent": is_coherent,
            "notes": [] if is_coherent else ["Non-linear degree sequence detected."],
        },
        "gaps": gaps,
        "data_quality": {
            "missing_fields_count": len(missing_paths),
            "unclear_fields_count": len(unclear_paths),
            "critical_missing": missing_paths[:12],
        },
    }


def _extract_json(raw_text: str) -> dict:
    text = raw_text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in education analysis response")
    return json.loads(text[start : end + 1])


def _build_education_prompt(facts: dict) -> tuple[str, str]:
    sys = (
        "You are TALASH Education Analyst. Answer only using provided education facts. "
        "Never hallucinate. Return strict JSON only."
    )
    qlist = [{"question_id": qid, "question": q} for qid, q in EDU_QUESTIONS]
    usr = (
        "Given the education facts and questions below, produce JSON with keys: "
        "answers (array), overall_education_assessment (object).\n"
        "Each answer item must have: question_id, question, answer, status(answered|insufficient_data), confidence(0-1), evidence_fields(array).\n"
        "overall_education_assessment must have: strength(weak|moderate|strong), summary, confidence(0-1).\n"
        f"FACTS:\n{json.dumps(facts, ensure_ascii=True)}\n"
        f"QUESTIONS:\n{json.dumps(qlist, ensure_ascii=True)}"
    )
    return sys, usr


async def run_education_llm_analysis(facts: dict, model_name: str) -> dict:
    if not settings.openrouter_api_key:
        raise RuntimeError("OPENROUTER_API_KEY missing")
    system_prompt, user_prompt = _build_education_prompt(facts)
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
        "X-Title": "TALASH Education Analyzer",
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
        raise ValueError("Education analysis response missing 'answers'")
    if "overall_education_assessment" not in result:
        raise ValueError("Education analysis response missing 'overall_education_assessment'")
    return result
