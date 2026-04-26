import json
import re

import httpx

from backend.config import settings


BOOKS_PATENTS_QUESTIONS = [
    ("bp_q1", "How substantial is the candidate's patents and books output overall?"),
    ("bp_q2", "Are the patents/books recent and relevant to the profile?"),
    ("bp_q3", "Does the balance of patents vs books suggest a coherent profile?"),
    ("bp_q4", "Are titles, years, and publishers/countries reasonably complete?"),
    ("bp_q5", "Is there evidence of sustained contribution or only isolated items?"),
    ("bp_q6", "Overall, how strong is this patents and books profile?"),
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


def compute_books_patents_facts(parsed_payload: dict) -> dict:
    patents = parsed_payload.get("patents", []) if isinstance(parsed_payload, dict) else []
    books = parsed_payload.get("books", []) if isinstance(parsed_payload, dict) else []

    patent_rows = []
    for idx, item in enumerate(patents):
        patent_rows.append(
            {
                "index": idx,
                "type": "patent",
                "title": _safe_field(item, "title").get("value", "missing"),
                "patent_number": _safe_field(item, "patent_number").get("value", "missing"),
                "year": _safe_field(item, "year").get("value", "missing"),
                "country": _safe_field(item, "country").get("value", "missing"),
                "inventors": item.get("inventors", []) if isinstance(item.get("inventors"), list) else [],
                "url": _safe_field(item, "url").get("value", "missing"),
            }
        )

    book_rows = []
    for idx, item in enumerate(books):
        book_rows.append(
            {
                "index": idx,
                "type": "book",
                "title": _safe_field(item, "title").get("value", "missing"),
                "authors": item.get("authors", []) if isinstance(item.get("authors"), list) else [],
                "isbn": _safe_field(item, "isbn").get("value", "missing"),
                "publisher": _safe_field(item, "publisher").get("value", "missing"),
                "year": _safe_field(item, "year").get("value", "missing"),
                "url": _safe_field(item, "url").get("value", "missing"),
            }
        )

    combined = [
        {"kind": "patent", **row, "year_sort": _extract_year(row["year"])} for row in patent_rows
    ] + [
        {"kind": "book", **row, "year_sort": _extract_year(row["year"])} for row in book_rows
    ]
    combined_sorted = sorted(combined, key=lambda x: (x.get("year_sort") or 0, x.get("kind", "")), reverse=True)

    return {
        "patents_count": len(patent_rows),
        "books_count": len(book_rows),
        "combined_count": len(combined_sorted),
        "combined_timeline": combined_sorted,
        "patents_table": patent_rows,
        "books_table": book_rows,
        "summary": {
            "has_patents": len(patent_rows) > 0,
            "has_books": len(book_rows) > 0,
            "has_multiple_items": len(combined_sorted) > 1,
        },
    }


def _extract_json(raw_text: str) -> dict:
    text = raw_text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in books/patents analysis response")
    return json.loads(text[start : end + 1])


def _build_books_patents_prompt(facts: dict) -> tuple[str, str]:
    sys = (
        "You are TALASH Books/Patents Analyst. Answer only using provided facts. "
        "Never hallucinate. Return strict JSON only."
    )
    qlist = [{"question_id": qid, "question": q} for qid, q in BOOKS_PATENTS_QUESTIONS]
    usr = (
        "Given the books/patents facts and questions below, produce JSON with keys: "
        "answers (array), overall_books_patents_assessment (object).\n"
        "Each answer item must have: question_id, question, answer, status(answered|insufficient_data), confidence(0-1), evidence_fields(array).\n"
        "overall_books_patents_assessment must have: strength(weak|moderate|strong), summary, confidence(0-1).\n"
        f"FACTS:\n{json.dumps(facts, ensure_ascii=True)}\n"
        f"QUESTIONS:\n{json.dumps(qlist, ensure_ascii=True)}"
    )
    return sys, usr


async def run_books_patents_llm_analysis(facts: dict, model_name: str) -> dict:
    if not settings.openrouter_api_key:
        raise RuntimeError("OPENROUTER_API_KEY missing")
    system_prompt, user_prompt = _build_books_patents_prompt(facts)
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
        "X-Title": "TALASH Books Patents Analyzer",
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
        raise ValueError("Books/Patents analysis response missing 'answers'")
    if "overall_books_patents_assessment" not in result:
        raise ValueError("Books/Patents analysis response missing 'overall_books_patents_assessment'")
    return result
