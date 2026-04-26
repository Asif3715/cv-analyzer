from typing import Literal

from pydantic import BaseModel, Field


StatusValue = Literal["present", "missing", "unclear"]


class EvidenceField(BaseModel):
    value: str = "missing"
    status: StatusValue = "missing"
    evidence: str = ""


class EducationItem(BaseModel):
    level: EvidenceField = Field(default_factory=EvidenceField)
    degree_title: EvidenceField = Field(default_factory=EvidenceField)
    specialization: EvidenceField = Field(default_factory=EvidenceField)
    institution: EvidenceField = Field(default_factory=EvidenceField)
    board_university: EvidenceField = Field(default_factory=EvidenceField)
    start_year: EvidenceField = Field(default_factory=EvidenceField)
    end_year: EvidenceField = Field(default_factory=EvidenceField)
    score_value: EvidenceField = Field(default_factory=EvidenceField)
    score_type: EvidenceField = Field(default_factory=EvidenceField)


class ExperienceItem(BaseModel):
    job_title: EvidenceField = Field(default_factory=EvidenceField)
    organization: EvidenceField = Field(default_factory=EvidenceField)
    employment_type: EvidenceField = Field(default_factory=EvidenceField)
    start_date: EvidenceField = Field(default_factory=EvidenceField)
    end_date: EvidenceField = Field(default_factory=EvidenceField)
    is_current: EvidenceField = Field(default_factory=EvidenceField)
    description: EvidenceField = Field(default_factory=EvidenceField)


class PublicationItem(BaseModel):
    title: EvidenceField = Field(default_factory=EvidenceField)
    pub_type: EvidenceField = Field(default_factory=EvidenceField)
    venue: EvidenceField = Field(default_factory=EvidenceField)
    year: EvidenceField = Field(default_factory=EvidenceField)
    authors: list[str] = Field(default_factory=list)
    doi: EvidenceField = Field(default_factory=EvidenceField)
    url: EvidenceField = Field(default_factory=EvidenceField)


class PatentItem(BaseModel):
    title: EvidenceField = Field(default_factory=EvidenceField)
    patent_number: EvidenceField = Field(default_factory=EvidenceField)
    year: EvidenceField = Field(default_factory=EvidenceField)
    country: EvidenceField = Field(default_factory=EvidenceField)
    inventors: list[str] = Field(default_factory=list)
    url: EvidenceField = Field(default_factory=EvidenceField)


class BookItem(BaseModel):
    title: EvidenceField = Field(default_factory=EvidenceField)
    authors: list[str] = Field(default_factory=list)
    isbn: EvidenceField = Field(default_factory=EvidenceField)
    publisher: EvidenceField = Field(default_factory=EvidenceField)
    year: EvidenceField = Field(default_factory=EvidenceField)
    url: EvidenceField = Field(default_factory=EvidenceField)


class SupervisionItem(BaseModel):
    student_name: EvidenceField = Field(default_factory=EvidenceField)
    level: EvidenceField = Field(default_factory=EvidenceField)
    role: EvidenceField = Field(default_factory=EvidenceField)
    graduation_year: EvidenceField = Field(default_factory=EvidenceField)


class AwardItem(BaseModel):
    title: EvidenceField = Field(default_factory=EvidenceField)
    issuer: EvidenceField = Field(default_factory=EvidenceField)
    year: EvidenceField = Field(default_factory=EvidenceField)


class SectionConfidence(BaseModel):
    section: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class CandidateProfile(BaseModel):
    name: EvidenceField = Field(default_factory=EvidenceField)
    email: EvidenceField = Field(default_factory=EvidenceField)
    phone: EvidenceField = Field(default_factory=EvidenceField)
    education: list[EducationItem] = Field(default_factory=list)
    experience: list[ExperienceItem] = Field(default_factory=list)
    skills: list[EvidenceField] = Field(default_factory=list)
    publications: list[PublicationItem] = Field(default_factory=list)
    patents: list[PatentItem] = Field(default_factory=list)
    books: list[BookItem] = Field(default_factory=list)
    supervision: list[SupervisionItem] = Field(default_factory=list)
    awards: list[AwardItem] = Field(default_factory=list)
    section_confidence: list[SectionConfidence] = Field(default_factory=list)
