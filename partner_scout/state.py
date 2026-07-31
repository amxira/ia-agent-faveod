"""LangGraph state schemas for Agent 2."""

from __future__ import annotations

from operator import add
from typing import Annotated, TypedDict

from partner_scout.models import ESNCompany, QualifiedPartner


class ScoutState(TypedDict):
    """Top-level graph state. Partners accumulate via the `add` reducer."""

    companies: list[ESNCompany]
    partners: Annotated[list[QualifiedPartner], add]


class CompanyBranchState(TypedDict):
    """State handed to each parallel per-company branch (via Send)."""

    company: ESNCompany
    partners: Annotated[list[QualifiedPartner], add]
