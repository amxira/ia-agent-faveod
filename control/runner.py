"""Programmatic agent runners (Task 6.1).

Each function runs one agent's graph in-process and writes its output files,
mirroring `python -m <agent> run ...` but callable from the dashboard and the
chat agent. Agents degrade gracefully when the LLM is unavailable.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from tender_hunter import config as tender_config
from tender_hunter.output.report import write_reports

from partner_scout import config as partner_config
from partner_scout.output.writer import write_partners

from event_mapper import config as event_config
from event_mapper.output.writer import write_outputs

log = logging.getLogger(__name__)


def run_tenders(
    sources: list[str] | None = None,
    recent_days: int = 0,
    limit: int = 0,
) -> dict[str, Any]:
    """Run Agent 1 (Tender Hunter) and write its reports."""
    from tender_hunter.graph import build_components, run_once

    started = time.time()
    if sources:
        tender_config.SOURCES = [s.strip() for s in sources if s.strip()]
    if recent_days and recent_days > 0:
        tender_config.RECENT_DAYS = int(recent_days)

    state = run_once(build_components())
    reports = list(state.get("reports", []))
    if limit and limit > 0:
        reports = reports[:limit]

    counts = write_reports(reports)
    return {
        "agent": "tender_hunter",
        "ok": True,
        "reports": len(reports),
        "high_value": counts.get("high_value", 0),
        "duration_s": round(time.time() - started, 1),
        "sources": tender_config.SOURCES,
        "recent_days": tender_config.RECENT_DAYS,
    }


def run_partners(
    source: str | None = None,
    countries: list[str] | None = None,
    limit: int = 0,
) -> dict[str, Any]:
    """Run Agent 2 (Partner Scout) and write its partner files."""
    from partner_scout.graph import build_components, run_once

    started = time.time()
    src = (source or partner_config.SEARCH_SOURCE).strip().lower()
    if countries:
        partner_config.TARGET_COUNTRIES = [c.strip() for c in countries if c.strip()]

    state = run_once(build_components(source=src))
    partners = list(state.get("partners", []))
    if limit and limit > 0:
        partners = partners[:limit]

    counts = write_partners(partners)
    return {
        "agent": "partner_scout",
        "ok": True,
        "partners": len(partners),
        "qualified": counts.get("qualified", 0),
        "duration_s": round(time.time() - started, 1),
        "source": src,
        "countries": partner_config.TARGET_COUNTRIES,
    }


def run_events(
    source: str | None = None,
    countries: list[str] | None = None,
    upcoming_days: int = 0,
    limit: int = 0,
) -> dict[str, Any]:
    """Run Agent 3 (Event Mapper & Lead Profiler) and write its outputs."""
    from event_mapper.graph import build_components, run_once

    started = time.time()
    src = (source or event_config.EVENT_SOURCE).strip().lower()
    if countries:
        event_config.EVENT_COUNTRIES = [c.strip() for c in countries if c.strip()]
    if upcoming_days and upcoming_days > 0:
        event_config.UPCOMING_DAYS = int(upcoming_days)

    state = run_once(build_components(source=src))
    events = list(state.get("events", []))
    leads = list(state.get("leads", []))
    if limit and limit > 0:
        leads = leads[:limit]

    counts = write_outputs(events, leads)
    return {
        "agent": "event_mapper",
        "ok": True,
        "events": len(events),
        "leads": counts.get("leads", 0),
        "priority_leads": counts.get("priority", 0),
        "duration_s": round(time.time() - started, 1),
        "source": src,
        "countries": event_config.EVENT_COUNTRIES,
        "upcoming_days": event_config.UPCOMING_DAYS,
    }
