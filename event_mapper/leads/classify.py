"""Decision-maker classification & seniority (Task 4.3, deterministic)."""

from __future__ import annotations

import re

_GOV = (
    "minister", "ministre", "secretary of state", "secrétaire d'état",
    "director general", "directeur général", "governor", "ambassador",
)
_C_PHRASES = (
    "chief information officer", "chief technology officer", "chief digital officer",
    "chief information security officer", "chief security officer",
    "chief data officer", "chief innovation officer", "chief executive", "chief operating",
)
_C_ACRONYMS = (r"\bcio\b", r"\bcto\b", r"\bcdo\b", r"\bciso\b", r"\bceo\b", r"\bcoo\b", r"\bpresident\b")
_DIRECTOR = (
    "director", "directeur", "head of", "vice president", r"\bvp\b",
    "managing director", "general manager", "responsable", "principal",
)
_MANAGER = ("manager", "lead")
_ENGINEER = ("engineer", "developer", "consultant", "specialist", "analyst", "architect", "administrator")


def classify_role(job_title: str) -> tuple[bool, str, str]:
    """Return (is_decision_maker, seniority, reason)."""
    title = (job_title or "").lower()
    if not title:
        return False, "unknown", ""

    if any(_has(t, title) for t in _GOV):
        return True, "government", "Government executive (minister/secretariat)"
    if any(_has(t, title) for t in _C_PHRASES) or any(re.search(t, title) for t in _C_ACRONYMS):
        label = next((p.title() for p in _C_PHRASES if _has(p, title)), "C-level")
        return True, "c_level", f"C-level technology executive ({label})"
    if any(_has(t, title) for t in _DIRECTOR):
        return True, "director", "IT Director / Head of Technology"
    if any(_has(t, title) for t in _MANAGER):
        return False, "manager", ""
    if any(_has(t, title) for t in _ENGINEER):
        return False, "engineer", ""
    return False, "other", ""


def _has(token: str, title: str) -> bool:
    return re.search(rf"\b{re.escape(token)}\b", title) is not None
