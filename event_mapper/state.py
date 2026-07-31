"""LangGraph state schemas for Agent 3."""

from __future__ import annotations

from operator import add
from typing import Annotated, TypedDict

from event_mapper.models import ITEvent, ProspectCard


class MapperState(TypedDict):
    """Top-level graph state. Leads accumulate via the `add` reducer."""

    events: list[ITEvent]
    leads: Annotated[list[ProspectCard], add]


class EventBranchState(TypedDict):
    """State handed to each parallel per-event branch (via Send)."""

    event: ITEvent
    leads: Annotated[list[ProspectCard], add]
