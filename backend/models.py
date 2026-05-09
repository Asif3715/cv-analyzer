import datetime as dt
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON, String

from database import Base


JSONType = JSON


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime,
        default=dt.datetime.utcnow,
        onupdate=dt.datetime.utcnow,
    )

    documents = relationship("CVDocument", back_populates="candidate")


class CVDocument(Base):
    __tablename__ = "cv_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    candidate_id: Mapped[str | None] = mapped_column(ForeignKey("candidates.id"), nullable=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    file_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False, default="application/pdf")
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    upload_source: Mapped[str | None] = mapped_column(String(32), nullable=True, default="web")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="uploaded")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime,
        default=dt.datetime.utcnow,
        onupdate=dt.datetime.utcnow,
    )

    candidate = relationship("Candidate", back_populates="documents")
    extraction = relationship("CVTextExtraction", back_populates="document", uselist=False)
    parsed_profile = relationship("CVParsedProfile", back_populates="document", uselist=False)
    education_analyses = relationship("EducationAnalysis", back_populates="document")
    skills_analyses = relationship("SkillsAnalysis", back_populates="document")
    experience_analyses = relationship("ExperienceAnalysis", back_populates="document")
    research_analyses = relationship("ResearchAnalysis", back_populates="document")
    jobs = relationship("ProcessingJob", back_populates="document")


class CVTextExtraction(Base):
    __tablename__ = "cv_text_extractions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(ForeignKey("cv_documents.id"), nullable=False)
    extraction_method: Mapped[str] = mapped_column(String(32), nullable=False)
    ocr_used: Mapped[bool] = mapped_column(Boolean, default=False)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    extracted_text: Mapped[str] = mapped_column(Text, nullable=False)
    text_char_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    document = relationship("CVDocument", back_populates="extraction")


class CVParsedProfile(Base):
    __tablename__ = "cv_parsed_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(ForeignKey("cv_documents.id"), nullable=False)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1")
    parsed_payload: Mapped[dict] = mapped_column(JSONType, nullable=False)
    missing_fields: Mapped[list | None] = mapped_column(JSONType, nullable=True)
    unclear_fields: Mapped[list | None] = mapped_column(JSONType, nullable=True)
    validation_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    parse_confidence: Mapped[float | None] = mapped_column(nullable=True)
    raw_llm_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    document = relationship("CVDocument", back_populates="parsed_profile")


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(ForeignKey("cv_documents.id"), nullable=False)
    step: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    document = relationship("CVDocument", back_populates="jobs")


class EducationAnalysis(Base):
    __tablename__ = "education_analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(ForeignKey("cv_documents.id"), nullable=False)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    facts_payload: Mapped[dict] = mapped_column(JSONType, nullable=False)
    answers_payload: Mapped[dict] = mapped_column(JSONType, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime,
        default=dt.datetime.utcnow,
        onupdate=dt.datetime.utcnow,
    )

    document = relationship("CVDocument", back_populates="education_analyses")


class SkillsAnalysis(Base):
    __tablename__ = "skills_analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(ForeignKey("cv_documents.id"), nullable=False)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    facts_payload: Mapped[dict] = mapped_column(JSONType, nullable=False)
    answers_payload: Mapped[dict] = mapped_column(JSONType, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime,
        default=dt.datetime.utcnow,
        onupdate=dt.datetime.utcnow,
    )

    document = relationship("CVDocument", back_populates="skills_analyses")


class ExperienceAnalysis(Base):
    __tablename__ = "experience_analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(ForeignKey("cv_documents.id"), nullable=False)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    facts_payload: Mapped[dict] = mapped_column(JSONType, nullable=False)
    answers_payload: Mapped[dict] = mapped_column(JSONType, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime,
        default=dt.datetime.utcnow,
        onupdate=dt.datetime.utcnow,
    )

    document = relationship("CVDocument", back_populates="experience_analyses")


class ResearchVerification(Base):
    __tablename__ = "research_verifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    claim_fingerprint: Mapped[str] = mapped_column(String(256), unique=True, nullable=False)
    claim_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    claim_year: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_best: Mapped[str | None] = mapped_column(String(64), nullable=True)
    verification_status: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float] = mapped_column(nullable=False, default=0.0)
    match_scores: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    matched_metadata: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    issues: Mapped[list | None] = mapped_column(JSONType, nullable=True)
    checked_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    expires_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)


class ResearchAnalysis(Base):
    __tablename__ = "research_analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(ForeignKey("cv_documents.id"), nullable=False)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    facts_payload: Mapped[dict] = mapped_column(JSONType, nullable=False)
    answers_payload: Mapped[dict] = mapped_column(JSONType, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime,
        default=dt.datetime.utcnow,
        onupdate=dt.datetime.utcnow,
    )

    document = relationship("CVDocument", back_populates="research_analyses")
