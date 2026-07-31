"""Pydantic domain models for Agent 2 - Partner Scout."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

GUARDRAIL = "Unspecified - Manual review required"

TECH_FOCUS = Literal[
    "custom_development",
    "mixed",
    "low_code_reseller",
    "proprietary_reseller",
    "unspecified",
]


class PageText(BaseModel):
    """Text extracted from one page of a company website."""

    url: str
    title: str = ""
    kind: str = "page"  # home | case_studies | references | partners | about | contact | services | work
    text: str = ""


class ESNCompany(BaseModel):
    """A discovered local IT services company (search result)."""

    id: str
    name: str
    country: str = ""
    website: str = ""
    source: str = "search"
    search_query: str = ""
    description: str = ""
    # Offline corpus support: pre-populated page texts (sample mode) are used
    # as-is instead of fetching the live site.
    pages: list[PageText] = Field(default_factory=list)
    raw: dict = Field(default_factory=dict)


class Citation(BaseModel):
    """Exact source reference for a piece of evidence."""

    document: str  # page URL
    kind: str = ""
    snippet: str


class ESNProfile(BaseModel):
    """LLM-extracted company profile, with anti-hallucination guardrails.

    Each factual list/field is only populated if its evidence quotes were
    verified verbatim against the fetched page texts. Fields the model could not
    support are listed in `fields_unspecified` and require manual review.
    """

    company_id: str = ""
    company_name: str = ""
    tech_focus: str = "unspecified"
    services: list[str] = Field(default_factory=list)
    client_references: list[str] = Field(default_factory=list)
    project_scale: str = "unspecified"  # startup|smb|enterprise|public_sector|mixed|unspecified
    employees_estimate: str = ""
    languages: list[str] = Field(default_factory=list)
    contact_url: str = ""
    website: str = ""
    country_confirmed: bool = False
    rationale: str = ""
    evidence: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    fields_unspecified: list[str] = Field(default_factory=list)
    guardrail: Optional[str] = None  # no_pages | content_too_thin | llm_unavailable | evidence_not_found | invalid_fields
    pages_analyzed: int = 0
    confidence: float = 0.0


class QualifiedPartner(BaseModel):
    """Final Agent-2 output for a single company (Task 3.3)."""

    partner_id: str
    company_name: str
    country: str = ""
    website: str = ""
    contact_url: str = ""
    size: str = ""
    project_scale: str = ""
    services: list[str] = Field(default_factory=list)
    client_references: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    tech_focus: str = "unspecified"
    affinity_score: float = 0.0
    affinity_grade: str = "POOR PARTNER FIT"
    qualified: bool = False
    disqualification_reason: str = ""
    requires_manual_review: bool = True
    pages_analyzed: int = 0
    source: str = ""
    profile: Optional[dict] = None
    generated_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(timespec="seconds")
    )
