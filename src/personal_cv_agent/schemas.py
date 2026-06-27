"""Typed contracts for job-aware CV generation."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


RoleFamily = Literal[
    "data_analyst",
    "data_engineer",
    "ai_engineer",
    "ml_engineer",
    "healthcare_ai",
    "product_ai",
    "consulting",
    "software_engineering",
    "unknown",
]

RelevanceArea = Literal[
    "summary",
    "skills",
    "experience",
    "projects",
    "certifications",
]


class JobAnalysis(BaseModel):
    """Structured view of a job posting."""

    role_title: str
    company: str | None = None
    location: str | None = None
    seniority: str | None = None
    role_family: RoleFamily = "unknown"
    must_have_skills: list[str] = Field(default_factory=list)
    nice_to_have_skills: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    raw_text: str


class RetrievalQuerySet(BaseModel):
    """Section-specific search queries for evidence retrieval."""

    summary_query: str
    skills_query: str
    experience_query: str
    projects_query: str
    certifications_query: str


class EvidenceItem(BaseModel):
    """Retrieved, metadata-rich career evidence."""

    evidence_id: str
    content: str
    source_type: str = "unknown"
    source_file: str = "unknown"
    section: str = "general"
    relevance_area: RelevanceArea


class EvidencePack(BaseModel):
    """All evidence retrieved for one job posting."""

    job: JobAnalysis
    queries: RetrievalQuerySet
    items: list[EvidenceItem] = Field(default_factory=list)


class CVPlan(BaseModel):
    """Conservative plan for a tailored Markdown CV."""

    target_title: str
    summary_angle: str
    skill_groups: list[str] = Field(default_factory=list)
    experience_focus: list[str] = Field(default_factory=list)
    project_focus: list[str] = Field(default_factory=list)
    certification_focus: list[str] = Field(default_factory=list)
    omitted_or_deemphasized: list[str] = Field(default_factory=list)


class MarkdownCV(BaseModel):
    """Generated Markdown CV plus evidence lineage."""

    markdown: str
    evidence_ids: list[str] = Field(default_factory=list)


class ValidationIssue(BaseModel):
    """Basic generation quality or evidence-safety issue."""

    severity: Literal["warning", "error"]
    message: str
    section: str | None = None


class ValidationReport(BaseModel):
    """Validation result for a generated Markdown CV."""

    passed: bool
    issues: list[ValidationIssue] = Field(default_factory=list)
    estimated_pages: float
    word_count: int
