"""Pydantic domain models for Agent 3 - Event Mapper & Lead Profiler."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

GUARDRAIL = "Unspecified - Manual review required"


class PageText(BaseModel):
    """Text extracted from one page of an event website."""

    url: str
    title: str = ""
    kind: str = "page"  # home | speakers | agenda | attendees | about
    text: str = ""


class ITEvent(BaseModel):
    """A discovered IT event / conference in a target market."""

    id: str
    name: str
    source: str = ""
    country: str = ""
    city: str = ""
    url: str = ""
    start_date: str = ""
    end_date: str = ""
    description: str = ""
    keywords_matched: list[str] = Field(default_factory=list)
    # Offline corpus support: pre-populated page texts (sample mode).
    pages: list[PageText] = Field(default_factory=list)
    raw: dict = Field(default_factory=dict)


class PersonRef(BaseModel):
    """A person extracted from an event page (Task 4.2, NER output)."""

    name: str
    job_title: str = ""
    company: str = ""
    role_evidence: list[str] = Field(default_factory=list)
    title_evidence: list[str] = Field(default_factory=list)
    verified: bool = False
    guardrail: Optional[str] = None


class ProspectCard(BaseModel):
    """Final Agent-3 output for a single lead (Task 4.3)."""

    lead_id: str
    person_name: str
    job_title: str = ""
    company: str = ""
    country: str = ""
    city: str = ""
    seniority: str = "unknown"  # government | c_level | director | manager | engineer | other | unknown
    decision_maker: bool = False
    decision_maker_reason: str = ""
    event_name: str = ""
    event_url: str = ""
    panel_topics: list[str] = Field(default_factory=list)
    key_challenges: str = ""
    lead_score: float = 0.0
    priority: str = "LOW PRIORITY"
    requires_manual_review: bool = True
    pages_analyzed: int = 0
    source: str = ""
    person: Optional[dict] = None
    generated_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(timespec="seconds")
    )
