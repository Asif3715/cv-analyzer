import datetime as dt
import asyncio
import hashlib
import json
import re
from difflib import SequenceMatcher
from collections import Counter

import httpx

from backend.config import settings
from backend.models import ResearchVerification


RESEARCH_QUESTIONS = [
    ("res_q1", "How strong is the candidate's publication quality and legitimacy overall?"),
    ("res_q2", "How strong are conference and journal venues based on available ranking evidence?"),
    ("res_q3", "What does authorship role suggest about contribution and leadership?"),
    ("res_q4", "Is the profile focused or broad in research topics?"),
    ("res_q5", "What collaboration pattern is visible from co-author evidence?"),
    ("res_q6", "Overall, how strong is this research profile with key concerns?"),
]


CORE_RANK_MAP = {
    "neurips": "A*",
    "icml": "A*",
    "iclr": "A*",
    "cvpr": "A*",
    "eccv": "A",
    "iccv": "A*",
    "kdd": "A*",
    "acl": "A*",
    "emnlp": "A",
    "naacl": "A",
    "aaai": "A*",
    "ijcai": "A*",
}


def _safe_field(item: dict, key: str) -> dict:
    v = item.get(key, {})
    if isinstance(v, dict):
        return v
    return {"value": "missing", "status": "missing", "evidence": ""}


def _norm_text(value: str) -> str:
    text = (value or "").strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text


def _extract_year(value: str) -> int | None:
    m = re.search(r"(19|20)\d{2}", value or "")
    if not m:
        return None
    return int(m.group(0))


def _fingerprint(pub: dict) -> str:
    parts = [
        _norm_text(_safe_field(pub, "doi").get("value", "")),
        _norm_text(_safe_field(pub, "url").get("value", "")),
        _norm_text(_safe_field(pub, "title").get("value", "")),
        _norm_text(_safe_field(pub, "year").get("value", "")),
        _norm_text(" ".join([str(a) for a in pub.get("authors", [])])),
    ]
    base = "|".join(parts)
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def _author_overlap(claim_authors: list[str], matched_authors: list[str]) -> float:
    if not claim_authors or not matched_authors:
        return 0.0
    claim = {_norm_text(a) for a in claim_authors if a}
    matched = {_norm_text(a) for a in matched_authors if a}
    if not claim:
        return 0.0
    return round(len(claim & matched) / len(claim), 2)


def _venue_rank(venue: str) -> str | None:
    v = _norm_text(venue)
    for key, rank in CORE_RANK_MAP.items():
        if key in v:
            return rank
    return None


def _doi_url(doi: str) -> str:
    value = (doi or "").strip()
    if not value or value.lower() in {"missing", "unclear"}:
        return ""
    if value.startswith("http://") or value.startswith("https://"):
        return value
    value = value.replace("doi:", "").strip()
    if value.startswith("doi.org/"):
        value = value.split("doi.org/", 1)[1].strip()
    return f"https://doi.org/{value}" if value else ""


def _infer_publication_type(candidate: dict) -> str:
    venue = _norm_text(candidate.get("venue", ""))
    source = _norm_text(candidate.get("source", ""))

    if any(token in venue for token in ["journal", "transactions", "letters", "review", "scientific reports", "nature", "plos"]):
        return "journal"
    if any(token in venue for token in ["conference", "proceedings", "symposium", "workshop", "conference on", "proceedings of"]):
        return "conference"
    if "workshop" in venue:
        return "workshop"
    if any(token in venue for token in ["book", "chapter", "handbook", "monograph"]):
        return "book_chapter"
    if any(token in venue for token in ["arxiv", "preprint", "biorxiv", "medrxiv"]):
        return "preprint"
    if source == "dblp" and venue:
        return "conference"
    return "unclear"


def _verified_publication_context(candidate: dict | None) -> dict:
    if not candidate:
        return {"publication_place": "", "publication_type": "unclear", "doi_url": ""}
    return {
        "publication_place": candidate.get("venue", "") or "",
        "publication_type": _infer_publication_type(candidate),
        "doi_url": _doi_url(candidate.get("doi", "")),
    }


def _token_set_ratio(a: str, b: str) -> float:
    a_tokens = {t for t in _norm_text(a).split() if t}
    b_tokens = {t for t in _norm_text(b).split() if t}
    if not a_tokens or not b_tokens:
        return 0.0
    a_joined = " ".join(sorted(a_tokens))
    b_joined = " ".join(sorted(b_tokens))
    return SequenceMatcher(None, a_joined, b_joined).ratio() * 100.0


def _score_candidate_match(claim: dict, candidate: dict) -> dict:
    claim_title = _safe_field(claim, "title").get("value", "")
    claim_year = _extract_year(_safe_field(claim, "year").get("value", ""))
    claim_authors = claim.get("authors", []) if isinstance(claim.get("authors"), list) else []
    claim_venue = _safe_field(claim, "venue").get("value", "")

    cand_title = candidate.get("title", "")
    cand_year = candidate.get("year")
    cand_authors = candidate.get("authors", [])
    cand_venue = candidate.get("venue", "")

    title_score = _token_set_ratio(claim_title, cand_title) / 100.0
    year_score = 1.0 if (claim_year and cand_year and int(cand_year) == int(claim_year)) else 0.0
    author_score = _author_overlap(claim_authors, cand_authors)
    venue_score = _token_set_ratio(claim_venue, cand_venue) / 100.0 if claim_venue else 0.0

    final = round((0.6 * title_score) + (0.2 * author_score) + (0.15 * year_score) + (0.05 * venue_score), 2)
    return {
        "title_score": round(title_score, 2),
        "author_score": round(author_score, 2),
        "year_score": round(year_score, 2),
        "venue_score": round(venue_score, 2),
        "final_score": final,
    }


async def _query_crossref_by_title(title: str) -> list[dict]:
    if not title or title.lower() in {"missing", "unclear"}:
        return []
    url = "https://api.crossref.org/works"
    params = {"query.title": title, "rows": 5}
    async with httpx.AsyncClient(timeout=20.0) as client:
        res = await client.get(url, params=params)
        res.raise_for_status()
        data = res.json()
    items = data.get("message", {}).get("items", [])
    out = []
    for i in items:
        title_list = i.get("title", [])
        author_list = i.get("author", [])
        out.append(
            {
                "source": "crossref",
                "title": title_list[0] if title_list else "",
                "year": (i.get("issued", {}).get("date-parts", [[None]])[0][0]),
                "authors": [
                    " ".join(filter(None, [a.get("given", ""), a.get("family", "")])).strip()
                    for a in author_list
                ],
                "venue": (i.get("container-title") or [""])[0],
                "doi": i.get("DOI", ""),
                "url": i.get("URL", ""),
            }
        )
    return out


async def _query_crossref_by_doi(doi: str) -> dict | None:
    value = _norm_text(doi)
    if not value or value in {"missing", "unclear"}:
        return None
    value = value.replace("doi:", "")
    value = value.replace("https://doi.org/", "").replace("http://doi.org/", "")
    if not value:
        return None

    url = f"https://api.crossref.org/works/{value}"
    async with httpx.AsyncClient(timeout=20.0) as client:
        res = await client.get(url)
        if res.status_code == 404:
            return None
        res.raise_for_status()
        item = res.json().get("message", {})

    title_list = item.get("title", [])
    author_list = item.get("author", [])
    return {
        "source": "crossref",
        "title": title_list[0] if title_list else "",
        "year": (item.get("issued", {}).get("date-parts", [[None]])[0][0]),
        "authors": [
            " ".join(filter(None, [a.get("given", ""), a.get("family", "")])).strip()
            for a in author_list
        ],
        "venue": (item.get("container-title") or [""])[0],
        "doi": item.get("DOI", ""),
        "url": item.get("URL", ""),
        "doi_exact_match": True,
    }


async def _query_openalex_by_title(title: str) -> list[dict]:
    if not title or title.lower() in {"missing", "unclear"}:
        return []
    url = "https://api.openalex.org/works"
    params = {"search": title, "per-page": 5}
    async with httpx.AsyncClient(timeout=20.0) as client:
        res = await client.get(url, params=params)
        res.raise_for_status()
        data = res.json()
    items = data.get("results", [])
    out = []
    for i in items:
        out.append(
            {
                "source": "openalex",
                "title": i.get("title", ""),
                "year": i.get("publication_year"),
                "authors": [a.get("author", {}).get("display_name", "") for a in i.get("authorships", [])],
                "venue": i.get("primary_location", {}).get("source", {}).get("display_name", ""),
                "doi": (i.get("doi", "") or "").replace("https://doi.org/", ""),
                "url": i.get("id", ""),
            }
        )
    return out


async def _query_dblp_by_title(title: str) -> list[dict]:
    if not title or title.lower() in {"missing", "unclear"}:
        return []
    url = "https://dblp.org/search/publ/api"
    params = {"q": title, "h": 5, "format": "json"}
    async with httpx.AsyncClient(timeout=20.0) as client:
        res = await client.get(url, params=params)
        res.raise_for_status()
        data = res.json()
    hits = data.get("result", {}).get("hits", {}).get("hit", [])
    out = []
    for h in hits:
        info = h.get("info", {})
        authors_raw = info.get("authors", {}).get("author", [])
        if isinstance(authors_raw, str):
            authors = [authors_raw]
        else:
            authors = [a if isinstance(a, str) else a.get("text", "") for a in authors_raw]
        out.append(
            {
                "source": "dblp",
                "title": info.get("title", ""),
                "year": _extract_year(str(info.get("year", ""))),
                "authors": authors,
                "venue": info.get("venue", ""),
                "doi": info.get("doi", ""),
                "url": info.get("url", ""),
            }
        )
    return out


async def _verify_single_publication(pub: dict, db, force_refresh: bool = False) -> dict:
    fp = _fingerprint(pub)
    cached = db.query(ResearchVerification).filter(ResearchVerification.claim_fingerprint == fp).first()
    now = dt.datetime.utcnow()
    if cached and not force_refresh and (cached.expires_at is None or cached.expires_at > now):
        matched_metadata = cached.matched_metadata or {}
        return {
            "claim_fingerprint": fp,
            "from_cache": True,
            "verification_status": cached.verification_status,
            "confidence": cached.confidence,
            "source_best": cached.source_best,
            "match_scores": cached.match_scores or {},
            "matched_metadata": matched_metadata,
            "issues": cached.issues or [],
        }

    title = _safe_field(pub, "title").get("value", "")
    doi = _safe_field(pub, "doi").get("value", "")
    claim_year = _safe_field(pub, "year").get("value", "")

    issues = []
    candidates = []

    if doi and doi.lower() not in {"missing", "unclear"}:
        try:
            doi_candidate = await _query_crossref_by_doi(doi)
            if doi_candidate:
                candidates.append(doi_candidate)
            doi_candidates = await _query_crossref_by_title(title)
            for c in doi_candidates:
                c["doi_exact_boost"] = _norm_text(c.get("doi", "")) == _norm_text(doi)
            candidates.extend(doi_candidates)
        except Exception:
            issues.append("doi_lookup_failed")

    if not candidates:
        try:
            crossref, openalex, dblp = await asyncio.gather(
                _query_crossref_by_title(title),
                _query_openalex_by_title(title),
                _query_dblp_by_title(title),
            )
        except Exception:
            # fall back to per-source isolation so one provider failure
            # does not block the entire claim
            crossref = []
            issues.append("crossref_lookup_failed")
            try:
                openalex = await _query_openalex_by_title(title)
            except Exception:
                openalex = []
                issues.append("openalex_lookup_failed")
            try:
                dblp = await _query_dblp_by_title(title)
            except Exception:
                dblp = []
                issues.append("dblp_lookup_failed")
        candidates.extend(crossref + openalex + dblp)

    best = None
    best_scores = {"final_score": 0.0}
    for c in candidates:
        scores = _score_candidate_match(pub, c)
        if c.get("doi_exact_match"):
            scores["final_score"] = max(scores["final_score"], 0.98)
        elif c.get("doi_exact_boost"):
            scores["final_score"] = min(1.0, scores["final_score"] + 0.3)
        if scores["final_score"] > best_scores["final_score"]:
            best_scores = scores
            best = c

    status = "unverified"
    conf = 0.2
    if best is not None:
        fs = best_scores["final_score"]
        if best.get("doi_exact_match") and fs >= 0.7:
            status = "verified"
            conf = max(fs, 0.95)
        elif fs >= 0.85:
            status = "verified"
            conf = fs
        elif fs >= 0.65:
            status = "partial"
            conf = fs
        else:
            status = "unverified"
            conf = fs
    else:
        issues.append("no_candidate_match")

    matched_metadata = best or {}
    matched_metadata["claim_year"] = claim_year
    verified_context = _verified_publication_context(best)
    matched_metadata["publication_place"] = verified_context["publication_place"]
    matched_metadata["publication_type"] = verified_context["publication_type"]
    matched_metadata["doi_url"] = verified_context["doi_url"]
    venue_rank = _venue_rank(matched_metadata.get("venue", ""))
    if venue_rank:
        matched_metadata["venue_rank"] = venue_rank

    # upsert cache
    expires_at = now + dt.timedelta(days=120)
    if cached:
        cached.claim_title = title
        cached.claim_year = claim_year
        cached.source_best = matched_metadata.get("source", None)
        cached.verification_status = status
        cached.confidence = float(conf)
        cached.match_scores = best_scores
        cached.matched_metadata = matched_metadata
        cached.issues = issues
        cached.checked_at = now
        cached.expires_at = expires_at
    else:
        row = ResearchVerification(
            claim_fingerprint=fp,
            claim_title=title,
            claim_year=claim_year,
            source_best=matched_metadata.get("source", None),
            verification_status=status,
            confidence=float(conf),
            match_scores=best_scores,
            matched_metadata=matched_metadata,
            issues=issues,
            checked_at=now,
            expires_at=expires_at,
        )
        db.add(row)
    db.commit()

    return {
        "claim_fingerprint": fp,
        "from_cache": False,
        "verification_status": status,
        "confidence": round(float(conf), 2),
        "source_best": matched_metadata.get("source"),
        "match_scores": best_scores,
        "matched_metadata": matched_metadata,
        "issues": issues,
    }


async def compute_research_facts(parsed_payload: dict, db, force_refresh_fingerprints: set[str] | None = None) -> dict:
    pubs = parsed_payload.get("publications", []) if isinstance(parsed_payload, dict) else []
    force_refresh_fingerprints = force_refresh_fingerprints or set()
    verification_rows = []
    all_topics = []
    coauthors = []

    for p in pubs:
        ver = await _verify_single_publication(p, db, force_refresh=_fingerprint(p) in force_refresh_fingerprints)
        verified_metadata = ver.get("matched_metadata", {}) if isinstance(ver, dict) else {}
        claim = {
            "title": _safe_field(p, "title").get("value", "missing"),
            "pub_type": _safe_field(p, "pub_type").get("value", "missing"),
            "venue": _safe_field(p, "venue").get("value", "missing"),
            "year": _safe_field(p, "year").get("value", "missing"),
            "authors": p.get("authors", []) if isinstance(p.get("authors"), list) else [],
            "doi": _safe_field(p, "doi").get("value", "missing"),
            "url": _safe_field(p, "url").get("value", "missing"),
        }

        tokens = [t for t in re.split(r"[^a-zA-Z0-9]+", _norm_text(claim["title"])) if len(t) > 3]
        all_topics.extend(tokens)
        coauthors.extend([_norm_text(a) for a in claim["authors"] if a])

        verification_rows.append(
            {
                "claim": claim,
                "verified_publication": {
                    "publication_type": verified_metadata.get("publication_type", "unclear"),
                    "publication_place": verified_metadata.get("publication_place", ""),
                    "doi_url": verified_metadata.get("doi_url", ""),
                },
                "verification": ver,
            }
        )

    status_counter = Counter([v["verification"]["verification_status"] for v in verification_rows])
    avg_conf = round(
        sum(v["verification"].get("confidence", 0.0) for v in verification_rows) / len(verification_rows), 2
    ) if verification_rows else 0.0

    top_topics = [t for t, _ in Counter(all_topics).most_common(12)]
    topic_diversity = round(len(set(all_topics)) / max(1, len(all_topics)), 2) if all_topics else 0.0

    coauthor_counter = Counter([c for c in coauthors if c])
    top_collaborators = [name for name, _ in coauthor_counter.most_common(10)]

    venue_ranks = Counter()
    for row in verification_rows:
        r = row["verification"].get("matched_metadata", {}).get("venue_rank")
        if r:
            venue_ranks[r] += 1

    return {
        "publications_count": len(verification_rows),
        "verification_summary": {
            "verified": status_counter.get("verified", 0),
            "partial": status_counter.get("partial", 0),
            "unverified": status_counter.get("unverified", 0),
            "average_confidence": avg_conf,
        },
        "venue_quality": {
            "rank_distribution": dict(venue_ranks),
        },
        "topic_variability": {
            "top_topics": top_topics,
            "diversity_score": topic_diversity,
        },
        "coauthor_analysis": {
            "unique_coauthors": len(set([c for c in coauthors if c])),
            "top_collaborators": top_collaborators,
            "repeat_collaboration_ratio": round(
                sum(1 for _, c in coauthor_counter.items() if c > 1) / max(1, len(coauthor_counter)),
                2,
            ) if coauthor_counter else 0.0,
        },
        "publication_verifications": verification_rows,
    }


def _extract_json(raw_text: str) -> dict:
    text = raw_text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in research analysis response")
    return json.loads(text[start : end + 1])


def extract_unverified_fingerprints(facts: dict) -> list[str]:
    rows = facts.get("publication_verifications", []) if isinstance(facts, dict) else []
    return [
        row.get("verification", {}).get("claim_fingerprint")
        for row in rows
        if row.get("verification", {}).get("verification_status") == "unverified"
        and row.get("verification", {}).get("claim_fingerprint")
    ]


def _build_research_prompt(facts: dict) -> tuple[str, str]:
    sys = (
        "You are TALASH Research Analyst. Answer only using provided research facts. "
        "Never hallucinate. Return strict JSON only."
    )
    qlist = [{"question_id": qid, "question": q} for qid, q in RESEARCH_QUESTIONS]
    usr = (
        "Given the research facts and questions below, produce JSON with keys: "
        "answers (array), overall_research_assessment (object).\n"
        "Each answer item must have: question_id, question, answer, status(answered|insufficient_data), confidence(0-1), evidence_fields(array).\n"
        "overall_research_assessment must have: strength(weak|moderate|strong), summary, confidence(0-1).\n"
        "Use verified_publication fields only for venue/place/type/doi references. Do not use claim fields when discussing publication venue or DOI.\n"
        f"FACTS:\n{json.dumps(facts, ensure_ascii=True)}\n"
        f"QUESTIONS:\n{json.dumps(qlist, ensure_ascii=True)}"
    )
    return sys, usr


async def run_research_llm_analysis(facts: dict, model_name: str) -> dict:
    if not settings.openrouter_api_key:
        raise RuntimeError("OPENROUTER_API_KEY missing")
    system_prompt, user_prompt = _build_research_prompt(facts)
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
        "X-Title": "TALASH Research Analyzer",
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
        raise ValueError("Research analysis response missing 'answers'")
    if "overall_research_assessment" not in result:
        raise ValueError("Research analysis response missing 'overall_research_assessment'")
    return result
