"""Pydantic domain models shared across the pipeline."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class TenderDocument(BaseModel):
    """A single document attached to a tender (PDF, DOCX, ...)."""

    name: str
    doc_type: str = "tender_document"
    url: Optional[str] = None
    local_path: Optional[str] = None
    page_count: Optional[int] = None


class Tender(BaseModel):
    """A discovered tender opportunity."""

    id: str
    source: str
    title: str
    country: str = ""
    region: str = ""
    agency: str = ""
    description: str = ""
    reference: str = ""
    currency: str = ""
    budget_estimate: Optional[str] = None
    deadline: Optional[str] = None
    publication_date: Optional[str] = None
    url: str = ""
    language: str = ""
    documents: list[TenderDocument] = Field(default_factory=list)
    raw: dict = Field(default_factory=dict)


class Citation(BaseModel):
    """Exact source reference for a piece of evidence."""

    document: str
    page: Optional[int] = None
    chunk_id: str = ""
    snippet: str


CriterionStatus = Literal[
    "SATISFIED",
    "PARTIAL",
    "NOT_SATISFIED",
    "Unspecified - Manual review required",
]

GUARDRAIL = "Unspecified - Manual review required"


class CriterionResult(BaseModel):
    """Evaluation of one Faveod criterion for one tender."""

    criterion: str
    label: str
    status: CriterionStatus
    similarity_score: float = 0.0
    confidence: float = 0.0
    rationale: str = ""
    guardrail: Optional[str] = None
    citations: list[Citation] = Field(default_factory=list)


class FaveodReport(BaseModel):
    """Final Agent-1 output for a single tender."""

    tender_id: str
    source: str
    title: str
    country: str = ""
    region: str = ""
    deadline: Optional[str] = None
    url: str = ""
    fit_score: float = 0.0
    fit_grade: str = "POOR FIT"
    requires_manual_review: bool = True
    documents_analyzed: int = 0
    criteria: list[CriterionResult] = Field(default_factory=list)
    summary: str = ""
    generated_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(timespec="seconds")
    )
    raw_llm: Optional[dict] = None
