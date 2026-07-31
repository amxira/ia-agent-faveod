"""Control layer (Task 6.1): programmatic agent runs + saved-items store.

Gives the dashboard and the chat agent a common way to run the three agents
in-process (no CLI commands) and to bookmark interesting results.
"""

from __future__ import annotations

from control.runner import run_events, run_partners, run_tenders
from control.saved import (
    KINDS,
    all_saved,
    is_saved,
    list_saved,
    remove_item,
    save_item,
)

__all__ = [
    "KINDS",
    "all_saved",
    "is_saved",
    "list_saved",
    "remove_item",
    "run_events",
    "run_partners",
    "run_tenders",
    "save_item",
]
