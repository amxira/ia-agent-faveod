"""Faveod Sovereign Intelligence - REST API (FastAPI).

This is the ONLY backend. All UI work happens in a frontend that consumes this
API (see FRONTEND.md). FastAPI ships with automatic documentation:
- Swagger UI:  http://localhost:8000/docs
- ReDoc:       http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

Run with:  python -m api   (uvicorn, reload off)
     or:  python -m api --reload
     or:  uvicorn api.app:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from api import schemas
from api.sessions import sessions
from chat.tools import _as_float, _as_int, _clean_query, _country_matches, _date_in_window, _matches
from control import runner as ctl
from control import saved as saved_store
from dashboard import data as store
from notifications import notifier

log = logging.getLogger(__name__)

app = FastAPI(
    title="Faveod Sovereign Intelligence API",
    version="1.0.0",
    description=(
        "Backend for the Faveod multi-agent intelligence system: tender hunting, "
        "partner scouting, event mapping / lead profiling, favorites, notifications "
        "and the Faveod Assist chat agent. Agents run in-process and write their "
        "output files under data/output/."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# The future frontend (React/Vue/Next) will likely run on another origin/port.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api"


def _find(items: list[dict], key: str, value: str) -> dict | None:
    for item in items:
        if str(item.get(key) or "") == value:
            return item
    return None


def _event_lead_counts() -> dict[str, int]:
    counts: dict[str, int] = {}
    for lead in store.load_leads():
        name = str(lead.get("event_name") or "")
        if name:
            counts[name] = counts.get(name, 0) + 1
    return counts


_ID_FIELDS = {"tenders": "tender_id", "partners": "partner_id", "leads": "lead_id"}


def _resolve_saved(kind: str, load_fn) -> dict[str, Any]:
    saved_ids = set(saved_store.list_saved(kind))
    id_key = _ID_FIELDS.get(kind, "id")
    items = [item for item in load_fn() if str(item.get(id_key)) in saved_ids]
    return {"kind": kind, "count": len(saved_ids), "items": items}


# --------------------------------------------------------------------------- #
# health & options
# --------------------------------------------------------------------------- #
@app.get(API_PREFIX + "/health", tags=["system"])
def health() -> dict:
    return {"status": "ok", "service": "faveod-api", "docs": "/docs"}


@app.get(API_PREFIX + "/agents/options", tags=["system"])
def agent_options() -> dict:
    """The backend source lists the frontend dropdowns should offer."""
    return {
        "tender_sources": schemas.TENDER_SOURCES,
        "partner_sources": schemas.PARTNER_SOURCES,
        "event_sources": schemas.EVENT_SOURCES,
        "countries": sorted(
            {
                str(c)
                for c in (
                    ["Morocco", "Senegal", "Tunisia", "Egypt", "Saudi Arabia", "United Arab Emirates"]
                )
            }
        ),
        "kinds": list(saved_store.KINDS),
    }


# --------------------------------------------------------------------------- #
# data: summary
# --------------------------------------------------------------------------- #
@app.get(API_PREFIX + "/summary", tags=["data"])
def summary() -> dict:
    """Global picture of the agents' latest outputs."""
    data = store.summary()
    data["saved"] = {kind: len(ids) for kind, ids in saved_store.all_saved().items()}
    return data


# --------------------------------------------------------------------------- #
# data: tenders
# --------------------------------------------------------------------------- #
@app.get(API_PREFIX + "/tenders", tags=["data"])
def list_tenders(
    query: str | None = None,
    country: str | None = None,
    min_score: float | None = Query(default=None, ge=0, le=100),
    recent_days: int = Query(default=0, ge=0),
    limit: int = Query(default=0, ge=0),
) -> dict:
    """Analyzed tender reports, sorted by fit score (desc)."""
    q = _clean_query(query)
    rows = []
    for rec in store.load_tenders():
        if not _matches(rec, q):
            continue
        if not _country_matches(rec, country):
            continue
        if _as_float(rec.get("fit_score")) < _as_float(min_score):
            continue
        if not _date_in_window(rec.get("publication_date") or rec.get("deadline"), _as_int(recent_days)):
            continue
        rows.append(rec)
    rows.sort(key=lambda r: r.get("fit_score") or 0, reverse=True)
    n = _as_int(limit)
    if n > 0:
        rows = rows[:n]
    return {"count": len(rows), "items": rows}


@app.get(API_PREFIX + "/tenders/{tender_id}", tags=["data"])
def get_tender(tender_id: str) -> dict:
    item = _find(store.load_tenders(), "tender_id", tender_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"tender {tender_id!r} not found")
    return item


# --------------------------------------------------------------------------- #
# data: partners
# --------------------------------------------------------------------------- #
@app.get(API_PREFIX + "/partners", tags=["data"])
def list_partners(
    query: str | None = None,
    country: str | None = None,
    qualified_only: bool = False,
    min_score: float | None = Query(default=None, ge=0, le=100),
    limit: int = Query(default=0, ge=0),
) -> dict:
    """Scouted partner companies, sorted by affinity score (desc)."""
    q = _clean_query(query)
    rows = []
    for rec in store.load_partners():
        if not _matches(rec, q):
            continue
        if not _country_matches(rec, country):
            continue
        if qualified_only and not rec.get("qualified"):
            continue
        if _as_float(rec.get("affinity_score")) < _as_float(min_score):
            continue
        rows.append(rec)
    rows.sort(key=lambda r: r.get("affinity_score") or 0, reverse=True)
    n = _as_int(limit)
    if n > 0:
        rows = rows[:n]
    return {"count": len(rows), "items": rows}


@app.get(API_PREFIX + "/partners/{partner_id}", tags=["data"])
def get_partner(partner_id: str) -> dict:
    item = _find(store.load_partners(), "partner_id", partner_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"partner {partner_id!r} not found")
    return item


# --------------------------------------------------------------------------- #
# data: events & leads
# --------------------------------------------------------------------------- #
@app.get(API_PREFIX + "/events", tags=["data"])
def list_events(
    query: str | None = None,
    country: str | None = None,
    upcoming_days: int = Query(default=0, ge=0),
    limit: int = Query(default=0, ge=0),
) -> dict:
    """Mapped IT events, ranked by profiled-lead count then start date."""
    q = _clean_query(query)
    lead_counts = _event_lead_counts()
    rows = []
    for rec in store.load_events():
        if not _matches(rec, q):
            continue
        if not _country_matches(rec, country):
            continue
        if _as_int(upcoming_days) and not _date_in_window(rec.get("start_date"), _as_int(upcoming_days)):
            continue
        item = dict(rec)
        item["lead_count"] = lead_counts.get(str(rec.get("name") or ""), 0)
        rows.append(item)
    rows.sort(key=lambda r: (-(r.get("lead_count") or 0), r.get("start_date") or ""))
    n = _as_int(limit)
    if n > 0:
        rows = rows[:n]
    return {"count": len(rows), "items": rows}


@app.get(API_PREFIX + "/events/{event_id}", tags=["data"])
def get_event(event_id: str) -> dict:
    item = _find(store.load_events(), "id", event_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"event {event_id!r} not found")
    item["lead_count"] = _event_lead_counts().get(str(item.get("name") or ""), 0)
    return item


@app.get(API_PREFIX + "/leads", tags=["data"])
def list_leads(
    query: str | None = None,
    country: str | None = None,
    min_score: float | None = Query(default=None, ge=0, le=100),
    priority: str | None = None,
    days: int = Query(default=0, ge=0),
    limit: int = Query(default=0, ge=0),
) -> dict:
    """Event-derived prospect cards, sorted by lead score (desc)."""
    q = _clean_query(query)
    rows = []
    for rec in store.load_leads():
        if not _matches(rec, q):
            continue
        if not _country_matches(rec, country):
            continue
        if _as_float(rec.get("lead_score")) < _as_float(min_score):
            continue
        if priority and priority.strip().lower() not in str(rec.get("priority") or "").lower():
            continue
        if _as_int(days) and not _date_in_window(
            rec.get("start_date") or rec.get("generated_at"), _as_int(days)
        ):
            continue
        rows.append(rec)
    rows.sort(key=lambda r: r.get("lead_score") or 0, reverse=True)
    n = _as_int(limit)
    if n > 0:
        rows = rows[:n]
    return {"count": len(rows), "items": rows}


@app.get(API_PREFIX + "/leads/{lead_id}", tags=["data"])
def get_lead(lead_id: str) -> dict:
    item = _find(store.load_leads(), "lead_id", lead_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"lead {lead_id!r} not found")
    return item


# --------------------------------------------------------------------------- #
# favorites
# --------------------------------------------------------------------------- #
@app.get(API_PREFIX + "/saved", tags=["favorites"])
def list_saved() -> dict:
    """All bookmarked items, resolved with their latest data."""
    return {
        "tenders": _resolve_saved("tenders", store.load_tenders),
        "partners": _resolve_saved("partners", store.load_partners),
        "leads": _resolve_saved("leads", store.load_leads),
    }


@app.post(API_PREFIX + "/saved/{kind}/{item_id}", tags=["favorites"])
def save(kind: str, item_id: str) -> dict:
    result = saved_store.save_item(kind, item_id)
    if not result.get("ok"):
        raise HTTPException(status_code=422, detail=result.get("reason", "invalid kind"))
    return result


@app.delete(API_PREFIX + "/saved/{kind}/{item_id}", tags=["favorites"])
def unsave(kind: str, item_id: str) -> dict:
    result = saved_store.remove_item(kind, item_id)
    if not result.get("ok"):
        raise HTTPException(status_code=422, detail=result.get("reason", "invalid kind"))
    return result


# --------------------------------------------------------------------------- #
# actions: run agents
# --------------------------------------------------------------------------- #
@app.post(API_PREFIX + "/run/tenders", tags=["actions"])
def run_tenders(body: schemas.RunTendersRequest) -> dict:
    """Run Agent 1 (Tender Hunter): scrape, analyze and score tenders."""
    return ctl.run_tenders(sources=body.sources, recent_days=body.recent_days, limit=body.limit)


@app.post(API_PREFIX + "/run/partners", tags=["actions"])
def run_partners(body: schemas.RunPartnersRequest) -> dict:
    """Run Agent 2 (Partner Scout): find and qualify local IT partners."""
    return ctl.run_partners(source=body.source, countries=body.countries, limit=body.limit)


@app.post(API_PREFIX + "/run/events", tags=["actions"])
def run_events(body: schemas.RunEventsRequest) -> dict:
    """Run Agent 3 (Event Mapper): map events and profile leads."""
    return ctl.run_events(
        source=body.source, countries=body.countries, upcoming_days=body.upcoming_days, limit=body.limit
    )


@app.post(API_PREFIX + "/notifications/check", tags=["actions"])
def notifications_check(body: schemas.NotificationsCheckRequest) -> dict:
    """Detect & dispatch new high-value tenders / high-priority leads."""
    return notifier.check(threshold=body.threshold, dry_run=body.dry_run, reset=body.reset)


# --------------------------------------------------------------------------- #
# chat
# --------------------------------------------------------------------------- #
@app.post(API_PREFIX + "/chat", tags=["chat"])
def chat(body: schemas.ChatRequest) -> dict:
    """Ask Faveod Assist a question. Returns the reply + full conversation."""
    session_id, assistant = sessions.get_or_create(body.session_id)
    reply = assistant.answer(body.message, max_steps=body.max_steps)
    return {"session_id": session_id, "reply": reply, "history": assistant.history}


@app.delete(API_PREFIX + "/chat/{session_id}", tags=["chat"])
def reset_chat(session_id: str) -> dict:
    """Forget a conversation."""
    return {"ok": sessions.drop(session_id), "session_id": session_id}


__all__ = ["app"]
