"""Request bodies for the Faveod REST API.

FastAPI turns these Pydantic models into the OpenAPI/Swagger documentation shown
at /docs, so field descriptions below are what the future frontend developer sees.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# Valid agent backends (same lists the old Streamlit dashboard exposed).
TENDER_SOURCES = ["sample", "world_bank", "ebrd", "afdb", "imf"]
PARTNER_SOURCES = ["sample", "searxng"]
EVENT_SOURCES = ["sample", "ten_times", "eventbrite", "luma", "news"]


class RunTendersRequest(BaseModel):
    sources: list[str] | None = Field(
        default=None,
        description=f"Data sources to scrape. Valid: {TENDER_SOURCES}.",
        examples=[["sample", "world_bank"]],
    )
    recent_days: int = Field(
        default=0, ge=0,
        description="Keep only tenders published/deadline within the last N days. 0 = all.",
    )
    limit: int = Field(
        default=0, ge=0,
        description="Cap the number of reports written. 0 = no cap.",
    )


class RunPartnersRequest(BaseModel):
    source: str | None = Field(
        default=None,
        description=f"Search backend. Valid: {PARTNER_SOURCES}.",
        examples=["sample"],
    )
    countries: list[str] | None = Field(
        default=None,
        description="Target countries (e.g. ['Morocco', 'Senegal']).",
    )
    limit: int = Field(default=0, ge=0, description="Cap the number of partners. 0 = no cap.")


class RunEventsRequest(BaseModel):
    source: str | None = Field(
        default=None,
        description=f"Event backend. Valid: {EVENT_SOURCES}.",
        examples=["sample"],
    )
    countries: list[str] | None = Field(
        default=None,
        description="Target countries (e.g. ['Egypt', 'UAE']).",
    )
    upcoming_days: int = Field(
        default=0, ge=0,
        description="Keep only events starting within the next N days. 0 = all.",
    )
    limit: int = Field(default=0, ge=0, description="Cap the number of leads. 0 = no cap.")


class NotificationsCheckRequest(BaseModel):
    threshold: float | None = Field(
        default=None,
        ge=0, le=100,
        description="Min tender fit score (%) that fires an alert. Defaults to TENDER_ALERT_THRESHOLD.",
    )
    dry_run: bool = Field(default=False, description="Print to console only, do not dispatch.")
    reset: bool = Field(default=False, description="Clear the dedup state before checking.")


class ChatRequest(BaseModel):
    message: str = Field(description="The user's question (FR / EN / AR).")
    session_id: str | None = Field(
        default=None,
        description="Optional session id for a stateful conversation. Omit to create a new one.",
    )
    max_steps: int = Field(
        default=5, ge=1, le=10,
        description="Max tool-calling steps before the assistant answers.",
    )
