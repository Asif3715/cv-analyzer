import hashlib

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from config import settings
from database import Base, engine, get_db
from education import compute_education_facts, run_education_llm_analysis
from books_patents import compute_books_patents_facts, run_books_patents_llm_analysis
from experience import compute_experience_facts, run_experience_llm_analysis
from models import (
    Candidate,
    CVDocument,
    CVParsedProfile,
    CVTextExtraction,
    EducationAnalysis,
    ExperienceAnalysis,
    ProcessingJob,
    ResearchAnalysis,
    ResearchVerification,
    SkillsAnalysis,
)
from parsing import collect_missing_unclear_fields, parse_cv_text_with_llm
from pdf_utils import extract_text_from_pdf_bytes
from research import compute_research_facts, extract_unverified_fingerprints, run_research_llm_analysis
from supervision import compute_supervision_facts, run_supervision_llm_analysis
from skills import compute_skills_facts, run_skills_llm_analysis
from storage import upload_pdf_to_supabase


app = FastAPI(title="TALASH Module 1 API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://cv-analyzer-drab.vercel.app/",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)


def add_job(db: Session, document_id: str, step: str, status: str, error_message: str | None = None, metadata: dict | None = None):
    job = ProcessingJob(
        document_id=document_id,
        step=step,
        status=status,
        error_message=error_message,
        metadata_json=metadata,
    )
    try:
        db.add(job)
        db.commit()
    except Exception:
        db.rollback()


def clear_document_analysis_cache(db: Session, document_id: str) -> None:
    db.query(EducationAnalysis).filter(EducationAnalysis.document_id == document_id).delete()
    db.query(SkillsAnalysis).filter(SkillsAnalysis.document_id == document_id).delete()
    db.query(ExperienceAnalysis).filter(ExperienceAnalysis.document_id == document_id).delete()
    db.query(ResearchAnalysis).filter(ResearchAnalysis.document_id == document_id).delete()
    db.query(ProcessingJob).filter(
        ProcessingJob.document_id == document_id,
        ProcessingJob.step.in_(
            [
                "books_patents_analysis",
                "books_patents_analysis_cached",
                "supervision_analysis_cached",
            ]
        ),
    ).delete(synchronize_session=False)


def _publication_fingerprint(pub: dict) -> str:
    doi = ""
    url = ""
    title = ""
    year = ""
    authors = ""

    if isinstance(pub.get("doi"), dict):
        doi = pub.get("doi", {}).get("value", "")
    if isinstance(pub.get("url"), dict):
        url = pub.get("url", {}).get("value", "")
    if isinstance(pub.get("title"), dict):
        title = pub.get("title", {}).get("value", "")
    if isinstance(pub.get("year"), dict):
        year = pub.get("year", {}).get("value", "")
    if isinstance(pub.get("authors"), list):
        authors = " ".join([str(a) for a in pub.get("authors", [])])

    return hashlib.sha256("|".join([doi, url, title, year, authors]).encode("utf-8")).hexdigest()


def clear_research_verification_cache(db: Session, parsed_payload: dict | None) -> None:
    if not isinstance(parsed_payload, dict):
        return
    fingerprints = []
    for pub in parsed_payload.get("publications", []):
        if isinstance(pub, dict):
            fingerprints.append(_publication_fingerprint(pub))
    if fingerprints:
        db.query(ResearchVerification).filter(ResearchVerification.claim_fingerprint.in_(fingerprints)).delete(synchronize_session=False)


async def process_document(db: Session, document: CVDocument, candidate: Candidate, raw: bytes, previous_parsed_payload: dict | None = None) -> dict:
    try:
        add_job(db, document.id, "extract_text", "started")
        text, method, page_count = extract_text_from_pdf_bytes(raw)
        if not text:
            raise ValueError("No text could be extracted from PDF")

        db.query(CVTextExtraction).filter(CVTextExtraction.document_id == document.id).delete()
        db.query(CVParsedProfile).filter(CVParsedProfile.document_id == document.id).delete()

        extraction = CVTextExtraction(
            document_id=document.id,
            extraction_method=method,
            ocr_used=False,
            page_count=page_count,
            extracted_text=text,
            text_char_count=len(text),
        )
        db.add(extraction)
        document.status = "text_extracted"
        db.commit()
        add_job(db, document.id, "extract_text", "success", metadata={"method": method, "chars": len(text)})

        add_job(db, document.id, "parse", "started", metadata={"chars": len(text)})
        parsed_result = await parse_cv_text_with_llm(text)
        payload = parsed_result.profile.model_dump()
        missing, unclear = collect_missing_unclear_fields(payload)

        parsed_row = CVParsedProfile(
            document_id=document.id,
            model_name=settings.openrouter_model,
            schema_version="v1",
            parsed_payload=payload,
            missing_fields=missing,
            unclear_fields=unclear,
            validation_passed=True,
            parse_confidence=0.8,
            raw_llm_response=parsed_result.raw_response,
        )
        clear_research_verification_cache(db, previous_parsed_payload)
        clear_document_analysis_cache(db, document.id)
        db.add(parsed_row)

        candidate.full_name = payload.get("name", {}).get("value") if isinstance(payload.get("name"), dict) else None
        candidate.email = payload.get("email", {}).get("value") if isinstance(payload.get("email"), dict) else None
        candidate.phone = payload.get("phone", {}).get("value") if isinstance(payload.get("phone"), dict) else None

        document.status = "parsed"
        db.commit()
        add_job(db, document.id, "parse", "success", metadata={"missing_count": len(missing), "unclear_count": len(unclear)})

        return {
            "file": document.file_name,
            "status": "success",
            "document_id": document.id,
            "file_path": document.file_path,
            "pipeline": {
                "storage_uploaded": True,
                "text_extracted": True,
                "parsed": True,
                "saved": True,
            },
            "missing_fields_count": len(missing),
            "unclear_fields_count": len(unclear),
            "summary": {
                "education_records": len(payload.get("education", [])),
                "experience_records": len(payload.get("experience", [])),
                "skills_count": len(payload.get("skills", [])),
                "publications_count": len(payload.get("publications", [])),
                "patents_count": len(payload.get("patents", [])),
                "books_count": len(payload.get("books", [])),
                "supervision_count": len(payload.get("supervision", [])),
                "awards_count": len(payload.get("awards", [])),
            },
            "parsed_payload": payload,
        }

    except Exception as exc:
        db.rollback()
        document.status = "failed"
        db.commit()
        add_job(db, document.id, "parse", "failed", error_message=str(exc))

        extraction_exists = (
            db.query(CVTextExtraction).filter(CVTextExtraction.document_id == document.id).first() is not None
        )
        return {
            "file": document.file_name,
            "status": "failed",
            "document_id": document.id,
            "file_path": document.file_path,
            "pipeline": {
                "storage_uploaded": True,
                "text_extracted": extraction_exists,
                "parsed": False,
                "saved": False,
            },
            "error": str(exc),
        }


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/")
def root() -> dict:
    return {
        "service": "TALASH Module 1 API",
        "status": "running",
        "endpoints": [
            "/health",
            "/upload",
            "/documents",
            "/documents/{id}/education/facts",
            "/documents/{id}/education/analyze",
            "/documents/{id}/education",
            "/documents/{id}/skills/facts",
            "/documents/{id}/skills/analyze",
            "/documents/{id}/skills",
            "/documents/{id}/experience/facts",
            "/documents/{id}/experience/analyze",
            "/documents/{id}/experience",
            "/documents/{id}/books-patents/facts",
            "/documents/{id}/books-patents/analyze",
            "/documents/{id}/books-patents",
            "/documents/{id}/supervision/facts",
            "/documents/{id}/supervision/analyze",
            "/documents/{id}/supervision",
            "/documents/{id}/research/facts",
            "/documents/{id}/research/analyze",
            "/documents/{id}/research",
            "/docs",
        ],
    }


@app.post("/upload")
async def upload_and_parse(
    files: list[UploadFile] = File(...),
    force_reprocess: bool = Form(False),
    db: Session = Depends(get_db),
) -> dict:
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    results = []

    for uploaded in files:
        document = None
        if not uploaded.filename.lower().endswith(".pdf"):
            results.append(
                {
                    "file": uploaded.filename,
                    "status": "failed",
                    "error": "Only PDF files are supported",
                }
            )
            continue

        raw = await uploaded.read()
        file_hash = hashlib.sha256(raw).hexdigest()

        existing = db.query(CVDocument).filter(CVDocument.file_hash == file_hash).first()
        if existing:
            if force_reprocess:
                try:
                    file_path = await upload_pdf_to_supabase(raw, uploaded.filename)
                    existing.file_name = uploaded.filename
                    existing.file_path = file_path
                    existing.file_size_bytes = len(raw)
                    existing.status = "uploaded"
                    db.commit()
                    db.refresh(existing)

                    candidate = existing.candidate
                    if candidate is None:
                        candidate = Candidate()
                        db.add(candidate)
                        db.commit()
                        db.refresh(candidate)
                        existing.candidate_id = candidate.id
                        db.commit()

                    previous_parsed_payload = existing.parsed_profile.parsed_payload if existing.parsed_profile else None
                    result = await process_document(db, existing, candidate, raw, previous_parsed_payload)
                    result["reprocessed"] = True
                    results.append(result)
                except Exception as exc:
                    db.rollback()
                    results.append(
                        {
                            "file": uploaded.filename,
                            "status": "failed",
                            "document_id": existing.id,
                            "error": f"Reprocess failed: {exc}",
                        }
                    )
                continue

            results.append(
                {
                    "file": uploaded.filename,
                    "status": "skipped",
                    "reason": "Duplicate file hash already exists",
                    "document_id": existing.id,
                    "file_path": existing.file_path,
                    "current_status": existing.status,
                }
            )
            continue

        candidate = Candidate()
        db.add(candidate)
        db.flush()

        try:
            file_path = await upload_pdf_to_supabase(raw, uploaded.filename)

            document = CVDocument(
                candidate_id=candidate.id,
                file_name=uploaded.filename,
                file_path=file_path,
                file_hash=file_hash,
                file_size_bytes=len(raw),
                status="uploaded",
            )
            db.add(document)
            db.commit()
            db.refresh(document)
            results.append(await process_document(db, document, candidate, raw))

        except Exception as exc:
            db.rollback()
            if document is not None and document.id is not None:
                document.status = "failed"
                db.commit()
                add_job(db, document.id, "parse", "failed", error_message=str(exc))
            results.append(
                {
                    "file": uploaded.filename,
                    "status": "failed",
                    "document_id": document.id if document is not None else None,
                    "error": str(exc),
                }
            )

    return {"results": results}


@app.post("/documents/{document_id}/reprocess")
async def reprocess_document(document_id: str, db: Session = Depends(get_db)) -> dict:
    document = db.query(CVDocument).filter(CVDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    extraction = db.query(CVTextExtraction).filter(CVTextExtraction.document_id == document_id).first()
    if extraction is None:
        raise HTTPException(status_code=400, detail="No extracted text available for this document")

    candidate = document.candidate
    if candidate is None:
        candidate = Candidate()
        db.add(candidate)
        db.commit()
        db.refresh(candidate)
        document.candidate_id = candidate.id
        db.commit()

    try:
        add_job(db, document.id, "reprocess", "started")
        previous_parsed_payload = document.parsed_profile.parsed_payload if document.parsed_profile else None
        parsed_result = await parse_cv_text_with_llm(extraction.extracted_text)
        payload = parsed_result.profile.model_dump()
        missing, unclear = collect_missing_unclear_fields(payload)

        db.query(CVParsedProfile).filter(CVParsedProfile.document_id == document.id).delete()
        clear_research_verification_cache(db, previous_parsed_payload)
        clear_document_analysis_cache(db, document.id)
        parsed_row = CVParsedProfile(
            document_id=document.id,
            model_name=settings.openrouter_model,
            schema_version="v1",
            parsed_payload=payload,
            missing_fields=missing,
            unclear_fields=unclear,
            validation_passed=True,
            parse_confidence=0.8,
            raw_llm_response=parsed_result.raw_response,
        )
        db.add(parsed_row)
        document.status = "parsed"
        db.commit()
        add_job(db, document.id, "reprocess", "success", metadata={"missing_count": len(missing), "unclear_count": len(unclear)})
        return {
            "document_id": document.id,
            "status": "success",
            "missing_fields_count": len(missing),
            "unclear_fields_count": len(unclear),
            "parsed_payload": payload,
        }
    except Exception as exc:
        db.rollback()
        document.status = "failed"
        db.commit()
        add_job(db, document.id, "reprocess", "failed", error_message=str(exc))
        raise HTTPException(status_code=500, detail=f"Reprocess failed: {exc}")


@app.get("/documents/{document_id}/education/facts")
def get_education_facts(document_id: str, db: Session = Depends(get_db)) -> dict:
    document = db.query(CVDocument).filter(CVDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if not document.parsed_profile:
        raise HTTPException(status_code=400, detail="Parsed profile is not available")

    parsed = document.parsed_profile.parsed_payload
    facts = compute_education_facts(parsed)
    return {
        "document_id": document.id,
        "status": "ready",
        "facts": facts,
    }


@app.post("/documents/{document_id}/education/analyze")
async def analyze_education(document_id: str, regenerate: bool = Form(False), db: Session = Depends(get_db)) -> dict:
    document = db.query(CVDocument).filter(CVDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if not document.parsed_profile:
        raise HTTPException(status_code=400, detail="Parsed profile is not available")

    latest = (
        db.query(EducationAnalysis)
        .filter(EducationAnalysis.document_id == document.id)
        .order_by(EducationAnalysis.created_at.desc())
        .first()
    )
    if latest and not regenerate:
        return {
            "document_id": document.id,
            "analysis_model": latest.model_name,
            "status": "completed",
            "facts": latest.facts_payload,
            "analysis": latest.answers_payload,
            "cached": True,
        }

    facts = compute_education_facts(document.parsed_profile.parsed_payload)
    model_name = settings.education_analysis_model or settings.openrouter_model
    analysis = await run_education_llm_analysis(facts, model_name)

    row = EducationAnalysis(
        document_id=document.id,
        model_name=model_name,
        facts_payload=facts,
        answers_payload=analysis,
    )
    db.add(row)
    db.commit()

    return {
        "document_id": document.id,
        "analysis_model": model_name,
        "status": "completed",
        "facts": facts,
        "analysis": analysis,
        "cached": False,
    }


@app.get("/documents/{document_id}/education")
def get_education(document_id: str, db: Session = Depends(get_db)) -> dict:
    document = db.query(CVDocument).filter(CVDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if not document.parsed_profile:
        raise HTTPException(status_code=400, detail="Parsed profile is not available")

    facts = compute_education_facts(document.parsed_profile.parsed_payload)
    latest = (
        db.query(EducationAnalysis)
        .filter(EducationAnalysis.document_id == document.id)
        .order_by(EducationAnalysis.created_at.desc())
        .first()
    )
    return {
        "document_id": document.id,
        "facts": facts,
        "analysis": latest.answers_payload if latest else None,
        "analysis_model": latest.model_name if latest else None,
    }


@app.get("/documents/{document_id}/skills/facts")
def get_skills_facts(document_id: str, db: Session = Depends(get_db)) -> dict:
    document = db.query(CVDocument).filter(CVDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if not document.parsed_profile:
        raise HTTPException(status_code=400, detail="Parsed profile is not available")

    parsed = document.parsed_profile.parsed_payload
    facts = compute_skills_facts(parsed)
    return {
        "document_id": document.id,
        "status": "ready",
        "facts": facts,
    }


@app.post("/documents/{document_id}/skills/analyze")
async def analyze_skills(document_id: str, regenerate: bool = Form(False), db: Session = Depends(get_db)) -> dict:
    document = db.query(CVDocument).filter(CVDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if not document.parsed_profile:
        raise HTTPException(status_code=400, detail="Parsed profile is not available")

    latest = (
        db.query(SkillsAnalysis)
        .filter(SkillsAnalysis.document_id == document.id)
        .order_by(SkillsAnalysis.created_at.desc())
        .first()
    )
    if latest and not regenerate:
        return {
            "document_id": document.id,
            "analysis_model": latest.model_name,
            "status": "completed",
            "facts": latest.facts_payload,
            "analysis": latest.answers_payload,
            "cached": True,
        }

    facts = compute_skills_facts(document.parsed_profile.parsed_payload)
    model_name = settings.skills_analysis_model or settings.openrouter_model
    analysis = await run_skills_llm_analysis(facts, model_name)

    row = SkillsAnalysis(
        document_id=document.id,
        model_name=model_name,
        facts_payload=facts,
        answers_payload=analysis,
    )
    db.add(row)
    db.commit()

    return {
        "document_id": document.id,
        "analysis_model": model_name,
        "status": "completed",
        "facts": facts,
        "analysis": analysis,
        "cached": False,
    }


@app.get("/documents/{document_id}/skills")
def get_skills(document_id: str, db: Session = Depends(get_db)) -> dict:
    document = db.query(CVDocument).filter(CVDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if not document.parsed_profile:
        raise HTTPException(status_code=400, detail="Parsed profile is not available")

    facts = compute_skills_facts(document.parsed_profile.parsed_payload)
    latest = (
        db.query(SkillsAnalysis)
        .filter(SkillsAnalysis.document_id == document.id)
        .order_by(SkillsAnalysis.created_at.desc())
        .first()
    )
    return {
        "document_id": document.id,
        "facts": facts,
        "analysis": latest.answers_payload if latest else None,
        "analysis_model": latest.model_name if latest else None,
    }


@app.get("/documents/{document_id}/experience/facts")
def get_experience_facts(document_id: str, db: Session = Depends(get_db)) -> dict:
    document = db.query(CVDocument).filter(CVDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if not document.parsed_profile:
        raise HTTPException(status_code=400, detail="Parsed profile is not available")

    parsed = document.parsed_profile.parsed_payload
    facts = compute_experience_facts(parsed)
    return {
        "document_id": document.id,
        "status": "ready",
        "facts": facts,
    }


@app.post("/documents/{document_id}/experience/analyze")
async def analyze_experience(document_id: str, regenerate: bool = Form(False), db: Session = Depends(get_db)) -> dict:
    document = db.query(CVDocument).filter(CVDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if not document.parsed_profile:
        raise HTTPException(status_code=400, detail="Parsed profile is not available")

    latest = (
        db.query(ExperienceAnalysis)
        .filter(ExperienceAnalysis.document_id == document.id)
        .order_by(ExperienceAnalysis.created_at.desc())
        .first()
    )
    if latest and not regenerate:
        return {
            "document_id": document.id,
            "analysis_model": latest.model_name,
            "status": "completed",
            "facts": latest.facts_payload,
            "analysis": latest.answers_payload,
            "cached": True,
        }

    facts = compute_experience_facts(document.parsed_profile.parsed_payload)
    model_name = settings.experience_analysis_model or settings.openrouter_model
    analysis = await run_experience_llm_analysis(facts, model_name)

    row = ExperienceAnalysis(
        document_id=document.id,
        model_name=model_name,
        facts_payload=facts,
        answers_payload=analysis,
    )
    db.add(row)
    db.commit()

    return {
        "document_id": document.id,
        "analysis_model": model_name,
        "status": "completed",
        "facts": facts,
        "analysis": analysis,
        "cached": False,
    }


@app.get("/documents/{document_id}/experience")
def get_experience(document_id: str, db: Session = Depends(get_db)) -> dict:
    document = db.query(CVDocument).filter(CVDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if not document.parsed_profile:
        raise HTTPException(status_code=400, detail="Parsed profile is not available")

    facts = compute_experience_facts(document.parsed_profile.parsed_payload)
    latest = (
        db.query(ExperienceAnalysis)
        .filter(ExperienceAnalysis.document_id == document.id)
        .order_by(ExperienceAnalysis.created_at.desc())
        .first()
    )
    return {
        "document_id": document.id,
        "facts": facts,
        "analysis": latest.answers_payload if latest else None,
        "analysis_model": latest.model_name if latest else None,
    }


@app.get("/documents/{document_id}/books-patents/facts")
def get_books_patents_facts(document_id: str, db: Session = Depends(get_db)) -> dict:
    document = db.query(CVDocument).filter(CVDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if not document.parsed_profile:
        raise HTTPException(status_code=400, detail="Parsed profile is not available")

    facts = compute_books_patents_facts(document.parsed_profile.parsed_payload)
    return {
        "document_id": document.id,
        "status": "ready",
        "facts": facts,
    }


@app.post("/documents/{document_id}/books-patents/analyze")
async def analyze_books_patents(document_id: str, regenerate: bool = Form(False), db: Session = Depends(get_db)) -> dict:
    document = db.query(CVDocument).filter(CVDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if not document.parsed_profile:
        raise HTTPException(status_code=400, detail="Parsed profile is not available")

    latest = (
        db.query(ProcessingJob)
        .filter(ProcessingJob.document_id == document.id, ProcessingJob.step == "books_patents_analysis")
        .order_by(ProcessingJob.created_at.desc())
        .first()
    )

    facts = compute_books_patents_facts(document.parsed_profile.parsed_payload)
    if latest and not regenerate:
        # books/patents analysis is lightweight; cached job existence is enough to skip the LLM call
        cached_row = (
            db.query(ProcessingJob)
            .filter(ProcessingJob.document_id == document.id, ProcessingJob.step == "books_patents_analysis_cached")
            .order_by(ProcessingJob.created_at.desc())
            .first()
        )
        if cached_row and cached_row.metadata_json:
            return {
                "document_id": document.id,
                "analysis_model": cached_row.metadata_json.get("model_name"),
                "status": "completed",
                "facts": facts,
                "analysis": cached_row.metadata_json.get("analysis"),
                "cached": True,
            }

    model_name = settings.education_analysis_model or settings.openrouter_model
    analysis = await run_books_patents_llm_analysis(facts, model_name)

    db.add(
        ProcessingJob(
            document_id=document.id,
            step="books_patents_analysis",
            status="success",
            metadata_json={"model_name": model_name},
        )
    )
    db.add(
        ProcessingJob(
            document_id=document.id,
            step="books_patents_analysis_cached",
            status="success",
            metadata_json={"model_name": model_name, "analysis": analysis},
        )
    )
    db.commit()

    return {
        "document_id": document.id,
        "analysis_model": model_name,
        "status": "completed",
        "facts": facts,
        "analysis": analysis,
        "cached": False,
    }


@app.get("/documents/{document_id}/books-patents")
def get_books_patents(document_id: str, db: Session = Depends(get_db)) -> dict:
    document = db.query(CVDocument).filter(CVDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if not document.parsed_profile:
        raise HTTPException(status_code=400, detail="Parsed profile is not available")

    facts = compute_books_patents_facts(document.parsed_profile.parsed_payload)
    cached_row = (
        db.query(ProcessingJob)
        .filter(ProcessingJob.document_id == document.id, ProcessingJob.step == "books_patents_analysis_cached")
        .order_by(ProcessingJob.created_at.desc())
        .first()
    )
    return {
        "document_id": document.id,
        "facts": facts,
        "analysis": cached_row.metadata_json.get("analysis") if cached_row and cached_row.metadata_json else None,
        "analysis_model": cached_row.metadata_json.get("model_name") if cached_row and cached_row.metadata_json else None,
    }


@app.get("/documents/{document_id}/supervision/facts")
def get_supervision_facts(document_id: str, db: Session = Depends(get_db)) -> dict:
    document = db.query(CVDocument).filter(CVDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if not document.parsed_profile:
        raise HTTPException(status_code=400, detail="Parsed profile is not available")

    facts = compute_supervision_facts(document.parsed_profile.parsed_payload)
    return {
        "document_id": document.id,
        "status": "ready",
        "facts": facts,
    }


@app.post("/documents/{document_id}/supervision/analyze")
async def analyze_supervision(document_id: str, regenerate: bool = Form(False), db: Session = Depends(get_db)) -> dict:
    document = db.query(CVDocument).filter(CVDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if not document.parsed_profile:
        raise HTTPException(status_code=400, detail="Parsed profile is not available")

    latest = (
        db.query(ProcessingJob)
        .filter(ProcessingJob.document_id == document.id, ProcessingJob.step == "supervision_analysis_cached")
        .order_by(ProcessingJob.created_at.desc())
        .first()
    )

    facts = compute_supervision_facts(document.parsed_profile.parsed_payload)
    if latest and not regenerate and latest.metadata_json:
        return {
            "document_id": document.id,
            "analysis_model": latest.metadata_json.get("model_name"),
            "status": "completed",
            "facts": facts,
            "analysis": latest.metadata_json.get("analysis"),
            "cached": True,
        }

    model_name = settings.openrouter_model
    analysis = await run_supervision_llm_analysis(facts, model_name)

    db.add(
        ProcessingJob(
            document_id=document.id,
            step="supervision_analysis_cached",
            status="success",
            metadata_json={"model_name": model_name, "analysis": analysis},
        )
    )
    db.commit()

    return {
        "document_id": document.id,
        "analysis_model": model_name,
        "status": "completed",
        "facts": facts,
        "analysis": analysis,
        "cached": False,
    }


@app.get("/documents/{document_id}/supervision")
def get_supervision(document_id: str, db: Session = Depends(get_db)) -> dict:
    document = db.query(CVDocument).filter(CVDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if not document.parsed_profile:
        raise HTTPException(status_code=400, detail="Parsed profile is not available")

    facts = compute_supervision_facts(document.parsed_profile.parsed_payload)
    cached_row = (
        db.query(ProcessingJob)
        .filter(ProcessingJob.document_id == document.id, ProcessingJob.step == "supervision_analysis_cached")
        .order_by(ProcessingJob.created_at.desc())
        .first()
    )
    return {
        "document_id": document.id,
        "facts": facts,
        "analysis": cached_row.metadata_json.get("analysis") if cached_row and cached_row.metadata_json else None,
        "analysis_model": cached_row.metadata_json.get("model_name") if cached_row and cached_row.metadata_json else None,
    }


@app.get("/documents/{document_id}/research/facts")
async def get_research_facts(document_id: str, db: Session = Depends(get_db)) -> dict:
    document = db.query(CVDocument).filter(CVDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if not document.parsed_profile:
        raise HTTPException(status_code=400, detail="Parsed profile is not available")

    facts = await compute_research_facts(document.parsed_profile.parsed_payload, db)
    return {
        "document_id": document.id,
        "status": "ready",
        "facts": facts,
    }


@app.post("/documents/{document_id}/research/recheck-unverified")
async def recheck_unverified_research(document_id: str, db: Session = Depends(get_db)) -> dict:
    document = db.query(CVDocument).filter(CVDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if not document.parsed_profile:
        raise HTTPException(status_code=400, detail="Parsed profile is not available")

    current_facts = await compute_research_facts(document.parsed_profile.parsed_payload, db)
    unverified_fingerprints = set(extract_unverified_fingerprints(current_facts))
    refreshed_facts = await compute_research_facts(
        document.parsed_profile.parsed_payload,
        db,
        force_refresh_fingerprints=unverified_fingerprints,
    )

    return {
        "document_id": document.id,
        "status": "completed",
        "rechecked_count": len(unverified_fingerprints),
        "facts": refreshed_facts,
    }


@app.post("/documents/{document_id}/research/analyze")
async def analyze_research(document_id: str, regenerate: bool = Form(False), db: Session = Depends(get_db)) -> dict:
    document = db.query(CVDocument).filter(CVDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if not document.parsed_profile:
        raise HTTPException(status_code=400, detail="Parsed profile is not available")

    latest = (
        db.query(ResearchAnalysis)
        .filter(ResearchAnalysis.document_id == document.id)
        .order_by(ResearchAnalysis.created_at.desc())
        .first()
    )
    if latest and not regenerate:
        return {
            "document_id": document.id,
            "analysis_model": latest.model_name,
            "status": "completed",
            "facts": latest.facts_payload,
            "analysis": latest.answers_payload,
            "cached": True,
        }

    facts = await compute_research_facts(document.parsed_profile.parsed_payload, db)
    model_name = settings.research_analysis_model or settings.openrouter_model
    analysis = await run_research_llm_analysis(facts, model_name)

    row = ResearchAnalysis(
        document_id=document.id,
        model_name=model_name,
        facts_payload=facts,
        answers_payload=analysis,
    )
    db.add(row)
    db.commit()

    return {
        "document_id": document.id,
        "analysis_model": model_name,
        "status": "completed",
        "facts": facts,
        "analysis": analysis,
        "cached": False,
    }


@app.get("/documents/{document_id}/research")
async def get_research(document_id: str, db: Session = Depends(get_db)) -> dict:
    document = db.query(CVDocument).filter(CVDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if not document.parsed_profile:
        raise HTTPException(status_code=400, detail="Parsed profile is not available")

    facts = await compute_research_facts(document.parsed_profile.parsed_payload, db)
    latest = (
        db.query(ResearchAnalysis)
        .filter(ResearchAnalysis.document_id == document.id)
        .order_by(ResearchAnalysis.created_at.desc())
        .first()
    )
    return {
        "document_id": document.id,
        "facts": facts,
        "analysis": latest.answers_payload if latest else None,
        "analysis_model": latest.model_name if latest else None,
    }


@app.get("/documents")
def list_documents(db: Session = Depends(get_db)) -> dict:
    rows = db.query(CVDocument).order_by(CVDocument.created_at.desc()).limit(50).all()
    output = [
        {
            "document_id": row.id,
            "file_name": row.file_name,
            "candidate_name": row.candidate.full_name if row.candidate else None,
            "file_path": row.file_path,
            "status": row.status,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]
    return {"documents": output}


@app.get("/documents/{document_id}")
def get_document(document_id: str, db: Session = Depends(get_db)) -> dict:
    row = db.query(CVDocument).filter(CVDocument.id == document_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")

    parsed = row.parsed_profile.parsed_payload if row.parsed_profile else None
    jobs = (
        db.query(ProcessingJob)
        .filter(ProcessingJob.document_id == row.id)
        .order_by(ProcessingJob.created_at.asc())
        .all()
    )
    return {
        "document_id": row.id,
        "file_name": row.file_name,
        "candidate_name": row.candidate.full_name if row.candidate else None,
        "file_path": row.file_path,
        "status": row.status,
        "parsed_payload": parsed,
        "jobs": [
            {
                "step": job.step,
                "status": job.status,
                "error_message": job.error_message,
                "created_at": job.created_at.isoformat(),
            }
            for job in jobs
        ],
    }
