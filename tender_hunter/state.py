"""LangGraph state schemas for Agent 1."""

from __future__ import annotations

from operator import add
from typing import Annotated, TypedDict

from tender_hunter.models import FaveodReport, Tender


class HunterState(TypedDict):
    """Top-level graph state. Reports accumulate via the `add` reducer."""

    tenders: list[Tender]
    reports: Annotated[list[FaveodReport], add]


class TenderBranchState(TypedDict):
    """State handed to each parallel per-tender branch (via Send)."""

    tender: Tender
    reports: Annotated[list[FaveodReport], add]
