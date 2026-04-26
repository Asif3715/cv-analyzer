import json
import asyncio
import ast
import re
from dataclasses import dataclass

import httpx
from pydantic import ValidationError

from backend.config import settings
from backend.schemas import CandidateProfile


SYSTEM_PROMPT = """You are a CV information extraction engine for TALASH.
Return ONLY strict JSON. No markdown. No extra keys.

Extraction rules:
1) Never hallucinate. Use only text evidence from CV input.
2) Extract the entire CV, not just the strongest section. No section may be skipped if evidence exists.
3) Research/publications are high priority because they are often long and easy to truncate, but education, experience, skills, supervision, books, patents, and awards are equally important and must all be extracted carefully.
4) Every atomic field must follow structure: {"value": str, "status": "present|missing|unclear", "evidence": str}.
5) If field absent -> value="missing", status="missing", evidence="".
6) If field ambiguous -> value="unclear", status="unclear", evidence=best short snippet.
7) Preserve original values (dates, CGPA, percentages, titles, names, DOI text, URLs) as written unless clearly stated.
8) Keep arrays empty only when the section truly is not present. Do not drop a section just because it is sparse.
9) For every section, include all distinct entries you can find. Do not keep only the first few items.
10) Never merge separate entries into one object.
11) If an item is partially visible, still include it with the visible fields and mark the rest as missing or unclear.
12) Skills must be evidence-backed using a nearby snippet in evidence.
13) For publications, venue must be specific (full journal/conference/workshop name), never generic labels like "Journal" or "Conference".
14) For publications, use one object per distinct paper. If the CV clearly mentions 15 papers, return up to 15 publication objects if the evidence supports them.
15) For publications, do not skip a paper because some metadata is missing. Even a title-only paper must be included.
16) Publication authors can be a single author or multiple authors. If only the first author or partial author list is visible, include the visible names.
17) For score_type, use one of: "cgpa", "percentage", "grade", "division", "missing", "unclear".
18) For pub_type, use one of: "journal", "conference", "workshop", "book_chapter", "preprint", "missing", "unclear".
19) Before answering, do a completeness check: name/contact, education, experience, skills, publications, patents, books, supervision, and awards.
20) If a field is visible but uncertain, prefer "unclear" rather than omitting it.
"""


USER_PROMPT_TEMPLATE = """Extract and return JSON with this exact top-level schema:
{
  "name": {"value": "", "status": "present|missing|unclear", "evidence": ""},
  "email": {"value": "", "status": "present|missing|unclear", "evidence": ""},
  "phone": {"value": "", "status": "present|missing|unclear", "evidence": ""},
  "education": [
    {
      "level": {"value": "", "status": "present|missing|unclear", "evidence": ""},
      "degree_title": {"value": "", "status": "present|missing|unclear", "evidence": ""},
      "specialization": {"value": "", "status": "present|missing|unclear", "evidence": ""},
      "institution": {"value": "", "status": "present|missing|unclear", "evidence": ""},
      "board_university": {"value": "", "status": "present|missing|unclear", "evidence": ""},
      "start_year": {"value": "", "status": "present|missing|unclear", "evidence": ""},
      "end_year": {"value": "", "status": "present|missing|unclear", "evidence": ""},
      "score_value": {"value": "", "status": "present|missing|unclear", "evidence": ""},
      "score_type": {"value": "", "status": "present|missing|unclear", "evidence": ""}
    }
  ],
  "experience": [
    {
      "job_title": {"value": "", "status": "present|missing|unclear", "evidence": ""},
      "organization": {"value": "", "status": "present|missing|unclear", "evidence": ""},
      "employment_type": {"value": "", "status": "present|missing|unclear", "evidence": ""},
      "start_date": {"value": "", "status": "present|missing|unclear", "evidence": ""},
      "end_date": {"value": "", "status": "present|missing|unclear", "evidence": ""},
      "is_current": {"value": "", "status": "present|missing|unclear", "evidence": ""},
      "description": {"value": "", "status": "present|missing|unclear", "evidence": ""}
    }
  ],
  "skills": [
    {"value": "", "status": "present|missing|unclear", "evidence": ""}
  ],
  "publications": [
    {
      "title": {"value": "", "status": "present|missing|unclear", "evidence": ""},
      "pub_type": {"value": "", "status": "present|missing|unclear", "evidence": ""},
      "venue": {"value": "", "status": "present|missing|unclear", "evidence": ""},
      "year": {"value": "", "status": "present|missing|unclear", "evidence": ""},
      "authors": [],
      "doi": {"value": "", "status": "present|missing|unclear", "evidence": ""},
      "url": {"value": "", "status": "present|missing|unclear", "evidence": ""}
    }
  ],
  "patents": [
    {
      "title": {"value": "", "status": "present|missing|unclear", "evidence": ""},
      "patent_number": {"value": "", "status": "present|missing|unclear", "evidence": ""},
      "year": {"value": "", "status": "present|missing|unclear", "evidence": ""},
      "country": {"value": "", "status": "present|missing|unclear", "evidence": ""},
      "inventors": [],
      "url": {"value": "", "status": "present|missing|unclear", "evidence": ""}
    }
  ],
  "books": [
    {
      "title": {"value": "", "status": "present|missing|unclear", "evidence": ""},
      "authors": [],
      "isbn": {"value": "", "status": "present|missing|unclear", "evidence": ""},
      "publisher": {"value": "", "status": "present|missing|unclear", "evidence": ""},
      "year": {"value": "", "status": "present|missing|unclear", "evidence": ""},
      "url": {"value": "", "status": "present|missing|unclear", "evidence": ""}
    }
  ],
  "supervision": [
    {
      "student_name": {"value": "", "status": "present|missing|unclear", "evidence": ""},
      "level": {"value": "", "status": "present|missing|unclear", "evidence": ""},
      "role": {"value": "", "status": "present|missing|unclear", "evidence": ""},
      "graduation_year": {"value": "", "status": "present|missing|unclear", "evidence": ""}
    }
  ],
  "awards": [
    {
      "title": {"value": "", "status": "present|missing|unclear", "evidence": ""},
      "issuer": {"value": "", "status": "present|missing|unclear", "evidence": ""},
      "year": {"value": "", "status": "present|missing|unclear", "evidence": ""}
    }
  ],
  "section_confidence": [
    {"section": "education", "confidence": 0.0}
  ]
}

Important:
- Include education records across SSE/HSSC/UG/PG/MS/MPhil/PhD when present.
- Capture every visible entry in education, experience, skills, publications, patents, books, supervision, and awards.
- For publications, capture every distinct paper mention. Even a single weakly described paper should become one publication object.
- For publications, capture full venue title/authors/year/doi/url if present. Avoid generic venue values.
- For publications, if DOI or URL is present anywhere near the paper mention, copy it into the matching publication entry.
- For research specifically, err on the side of including a paper with missing/unclear fields rather than skipping it.
- For experience, preserve date strings exactly when format uncertain.
- Output valid JSON only.

CV TEXT:
__CV_TEXT__
"""


@dataclass
class ParseResult:
    profile: CandidateProfile
    raw_response: str


GENERIC_VENUES = {
    "journal",
    "international journal",
    "conference",
    "international conference",
    "proceedings",
    "conference proceeding",
}


def _normalize_field_status(field: dict) -> None:
    value = str(field.get("value", "missing") or "missing").strip()
    status = str(field.get("status", "missing") or "missing").strip().lower()
    evidence = str(field.get("evidence", "") or "").strip()

    if status not in {"present", "missing", "unclear"}:
        status = "missing"

    if not value:
        value = "missing"
    if value.lower() == "missing":
        status = "missing"
        evidence = ""
    elif value.lower() == "unclear" and status == "present":
        status = "unclear"

    field["value"] = value
    field["status"] = status
    field["evidence"] = evidence


def _normalize_level(level: str) -> str:
    l = level.lower()
    if l in {"ssc", "sse", "matric", "matriculation"}:
        return "SSE"
    if l in {"hssc", "intermediate", "fsc", "fa"}:
        return "HSSC"
    if "phd" in l:
        return "PhD"
    if "mphil" in l or "m.phil" in l:
        return "MPhil"
    if l == "ms" or re.search(r"\bms\b", l):
        return "MS"
    if any(token in l for token in ["bsc", "bs", "be", "bachelor"]):
        return "UG"
    if any(token in l for token in ["msc", "ma", "master"]):
        return "PG"
    return level


def _infer_score_type(value: str) -> str:
    v = value.strip().lower()
    if not v or v in {"missing", "unclear"}:
        return "missing"
    if any(token in v for token in ["grade", "a+", "a", "b+", "b", "c+"]):
        return "grade"
    if "division" in v:
        return "division"
    if any(token in v for token in ["cgpa", "gpa"]):
        return "cgpa"
    if any(token in v for token in ["%", "percent", "percentage", "%age"]):
        return "percentage"

    numeric = re.findall(r"\d+(?:\.\d+)?", v)
    if numeric:
        n = float(numeric[0])
        if n <= 4.5:
            return "cgpa"
        if 4.5 < n <= 100:
            return "percentage"
    return "unclear"


def _normalize_is_current(value: str) -> str:
    v = value.strip().lower()
    if v in {"true", "yes", "present", "current"}:
        return "true"
    if v in {"false", "no", "ended", "past"}:
        return "false"
    return value


def _section_confidence(payload: dict, section: str) -> float:
    node = payload.get(section)
    if node is None:
        return 0.0

    total = 0
    score = 0.0

    def walk(x):
        nonlocal total, score
        if isinstance(x, dict):
            if {"value", "status", "evidence"}.issubset(set(x.keys())):
                total += 1
                status = x.get("status")
                if status == "present":
                    score += 1.0
                elif status == "unclear":
                    score += 0.5
                return
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(node)
    if total == 0:
        return 0.0
    return round(score / total, 2)


def normalize_payload(payload: dict) -> dict:
    for key in ["name", "email", "phone"]:
        if isinstance(payload.get(key), dict):
            _normalize_field_status(payload[key])

    for edu in payload.get("education", []):
        for field in edu.values():
            if isinstance(field, dict):
                _normalize_field_status(field)

        level_field = edu.get("level", {})
        if isinstance(level_field, dict) and level_field.get("status") == "present":
            level_field["value"] = _normalize_level(level_field.get("value", ""))

        score_type = edu.get("score_type", {})
        score_value = edu.get("score_value", {})
        if isinstance(score_type, dict) and isinstance(score_value, dict):
            inferred = _infer_score_type(score_value.get("value", ""))
            current = score_type.get("value", "").strip().lower()
            if current in {"%age", "percent", "percentage"}:
                score_type["value"] = "percentage"
                score_type["status"] = "present"
            elif current in {"gpa", "cgpa"}:
                score_type["value"] = "cgpa"
                score_type["status"] = "present"
            elif score_type.get("status") in {"missing", "unclear"} and inferred != "missing":
                score_type["value"] = inferred
                score_type["status"] = "present" if inferred != "unclear" else "unclear"

    for exp in payload.get("experience", []):
        for field in exp.values():
            if isinstance(field, dict):
                _normalize_field_status(field)

        is_current = exp.get("is_current", {})
        end_date = exp.get("end_date", {})
        if isinstance(is_current, dict):
            is_current["value"] = _normalize_is_current(is_current.get("value", ""))
            if is_current["status"] in {"missing", "unclear"} and isinstance(end_date, dict):
                end_v = end_date.get("value", "").lower()
                if any(token in end_v for token in ["present", "current", "ongoing"]):
                    is_current["value"] = "true"
                    is_current["status"] = "present"
                elif end_v not in {"", "missing", "unclear"}:
                    is_current["value"] = "false"
                    is_current["status"] = "present"

    for skill in payload.get("skills", []):
        if isinstance(skill, dict):
            _normalize_field_status(skill)

    for pub in payload.get("publications", []):
        for key, field in pub.items():
            if key in {"authors"}:
                continue
            if isinstance(field, dict):
                _normalize_field_status(field)

        pub_type = pub.get("pub_type", {})
        if isinstance(pub_type, dict) and pub_type.get("status") == "present":
            p = pub_type.get("value", "").strip().lower()
            mapping = {
                "journal": "journal",
                "conference": "conference",
                "workshop": "workshop",
                "book chapter": "book_chapter",
                "book_chapter": "book_chapter",
                "preprint": "preprint",
            }
            pub_type["value"] = mapping.get(p, p if p else "unclear")
            if pub_type["value"] not in {"journal", "conference", "workshop", "book_chapter", "preprint"}:
                pub_type["status"] = "unclear"
                pub_type["value"] = "unclear"

        venue = pub.get("venue", {})
        if isinstance(venue, dict):
            vv = venue.get("value", "").strip().lower()
            if vv in GENERIC_VENUES:
                venue["value"] = "unclear"
                venue["status"] = "unclear"

        doi = pub.get("doi", {})
        if isinstance(doi, dict) and doi.get("status") == "present":
            dv = doi.get("value", "")
            doi["value"] = dv.replace("doi:", "").strip()

        if isinstance(pub.get("authors"), list):
            pub["authors"] = [str(a).strip() for a in pub["authors"] if str(a).strip()]

    for section in ["patents", "books", "supervision", "awards"]:
        for item in payload.get(section, []):
            for key, field in item.items():
                if key in {"authors", "inventors"}:
                    if isinstance(field, list):
                        item[key] = [str(x).strip() for x in field if str(x).strip()]
                    continue
                if isinstance(field, dict):
                    _normalize_field_status(field)

    payload["section_confidence"] = [
        {"section": "education", "confidence": _section_confidence(payload, "education")},
        {"section": "experience", "confidence": _section_confidence(payload, "experience")},
        {"section": "skills", "confidence": _section_confidence(payload, "skills")},
        {"section": "publications", "confidence": _section_confidence(payload, "publications")},
        {"section": "patents", "confidence": _section_confidence(payload, "patents")},
        {"section": "books", "confidence": _section_confidence(payload, "books")},
        {"section": "supervision", "confidence": _section_confidence(payload, "supervision")},
        {"section": "awards", "confidence": _section_confidence(payload, "awards")},
    ]

    return payload


def _extract_json(raw_text: str) -> dict:
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.replace("json", "", 1).strip()

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in model response")

    candidate = text[start : end + 1]

    # Attempt 1: strict JSON
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    # Attempt 2: common cleanup for LLM-style JSON-like output
    cleaned = candidate
    cleaned = cleaned.replace("\u201c", '"').replace("\u201d", '"').replace("\u2018", "'").replace("\u2019", "'")
    cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)  # trailing commas
    cleaned = re.sub(r"([{,]\s*)([A-Za-z_][A-Za-z0-9_\-]*)(\s*:)", r'\1"\2"\3', cleaned)  # bare keys

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Attempt 3: Python-literal style dict/list
    try:
        literal_obj = ast.literal_eval(cleaned)
        if isinstance(literal_obj, dict):
            return literal_obj
    except Exception:
        pass

    # Final failure with concise context
    preview = cleaned[:500].replace("\n", " ")
    raise ValueError(f"Model response is not valid JSON. Preview: {preview}")


async def parse_cv_text_with_llm(cv_text: str) -> ParseResult:
    if not settings.openrouter_api_key:
        raise RuntimeError("OPENROUTER_API_KEY is missing. Add it in .env.")

    prompt_text = USER_PROMPT_TEMPLATE.replace("__CV_TEXT__", cv_text)

    payload = {
        "model": settings.openrouter_model,
        "temperature": 0.0,
        "top_p": 0.9,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt_text},
        ],
    }

    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-Title": "TALASH Parser",
    }

    data = None
    last_error: Exception | None = None
    async with httpx.AsyncClient(timeout=120.0) as client:
        for attempt in range(4):
            try:
                response = await client.post(
                    f"{settings.openrouter_base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    wait_s = 2 ** attempt
                    if retry_after and retry_after.isdigit():
                        wait_s = max(wait_s, int(retry_after))
                    if attempt < 3:
                        await asyncio.sleep(wait_s)
                        continue
                    raise ValueError(
                        "OpenRouter rate limit hit (429). "
                        "Please wait a minute and retry, or switch to another model/provider."
                    )
                response.raise_for_status()
                data = response.json()
                break
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if exc.response.status_code == 429 and attempt < 3:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise
            except Exception as exc:
                last_error = exc
                if attempt < 3:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise

    if data is None:
        if last_error is not None:
            raise last_error
        raise ValueError("OpenRouter response missing after retries")

    raw_response = data["choices"][0]["message"]["content"]
    parsed = _extract_json(raw_response)
    try:
        profile = CandidateProfile.model_validate(parsed)
        normalized_payload = normalize_payload(profile.model_dump())
        profile = CandidateProfile.model_validate(normalized_payload)
    except ValidationError as exc:
        raise ValueError(f"Parsed JSON failed schema validation: {exc}") from exc
    return ParseResult(profile=profile, raw_response=raw_response)


def collect_missing_unclear_fields(payload: dict) -> tuple[list[str], list[str]]:
    missing: list[str] = []
    unclear: list[str] = []

    def walk(node, path: str):
        if isinstance(node, dict):
            if {"value", "status", "evidence"}.issubset(set(node.keys())):
                status = node.get("status")
                if status == "missing":
                    missing.append(path)
                elif status == "unclear":
                    unclear.append(path)
                return
            for key, value in node.items():
                child_path = f"{path}.{key}" if path else key
                walk(value, child_path)
        elif isinstance(node, list):
            for index, item in enumerate(node):
                walk(item, f"{path}[{index}]")

    walk(payload, "")
    return missing, unclear
