"""Chat agent tools (Task 6.2).

The assistant picks a tool by name; tools either read the agents' stored
outputs or run an agent in-process. Results are handed back to the model as
JSON so it can produce the final answer.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from dashboard import data as store
from control import runner, saved

log = logging.getLogger(__name__)


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, str):
        return [x.strip() for x in value.split(",") if x.strip()]
    return list(value)


def _as_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _date_in_window(value, days: int) -> bool:
    if not value or days <= 0:
        return True
    text = str(value).strip()[:19]
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            date = datetime.strptime(text, fmt)
        except ValueError:
            continue
        cutoff = datetime.utcnow() - timedelta(days=days)
        return date >= cutoff
    return True


def _matches(record: dict, query: str | None) -> bool:
    if not query:
        return True
    haystack = " ".join(str(v) for v in record.values() if v is not None).lower()
    return query.lower() in haystack


def _country_matches(record: dict, country: str | None) -> bool:
    if not country:
        return True
    value = str(record.get("country") or "").lower()
    wanted = country.strip().lower()
    return wanted in value


def _limit(items: list, limit) -> list:
    n = _as_int(limit, 10)
    if n <= 0:
        n = 10
    return items[:n]


def _compact(record: dict, keys: tuple[str, ...]) -> dict:
    return {k: record.get(k) for k in keys if k in record}


def tool_dashboard_summary():
    """Overall picture of the agents' latest outputs."""
    data = store.summary()
    data["saved"] = {k: len(v) for k, v in saved.all_saved().items()}
    return data


def tool_search_tenders(query=None, country=None, min_score=None, recent_days=None, limit=10):
    """Search the analyzed tender reports."""
    records = store.load_tenders()
    min_score = _as_float(min_score)
    recent_days = _as_int(recent_days)
    out = []
    for rec in records:
        if not _matches(rec, query):
            continue
        if not _country_matches(rec, country):
            continue
        if _as_float(rec.get("fit_score")) < min_score:
            continue
        if not _date_in_window(rec.get("publication_date") or rec.get("deadline"), recent_days):
            continue
        out.append(_compact(rec, ("tender_id", "title", "country", "fit_score", "fit_grade", "deadline", "url")))
    out.sort(key=lambda r: r.get("fit_score") or 0, reverse=True)
    return {"count": len(out), "items": _limit(out, limit)}


def tool_search_partners(query=None, country=None, min_score=None, limit=10):
    """Search the discovered partner companies."""
    records = store.load_partners()
    min_score = _as_float(min_score)
    out = []
    for rec in records:
        if not _matches(rec, query):
            continue
        if not _country_matches(rec, country):
            continue
        if _as_float(rec.get("affinity_score")) < min_score:
            continue
        out.append(_compact(rec, ("partner_id", "company_name", "country", "affinity_score", "affinity_grade", "qualified", "website")))
    out.sort(key=lambda r: r.get("affinity_score") or 0, reverse=True)
    return {"count": len(out), "items": _limit(out, limit)}


def tool_search_leads(query=None, country=None, min_score=None, priority=None, limit=10):
    """Search the event-derived leads / prospects."""
    records = store.load_leads()
    min_score = _as_float(min_score)
    out = []
    for rec in records:
        if not _matches(rec, query):
            continue
        if not _country_matches(rec, country):
            continue
        if _as_float(rec.get("lead_score")) < min_score:
            continue
        if priority and priority.strip().lower() not in str(rec.get("priority") or "").lower():
            continue
        out.append(_compact(rec, ("lead_id", "person_name", "job_title", "company", "country", "lead_score", "priority", "event_name")))
    out.sort(key=lambda r: r.get("lead_score") or 0, reverse=True)
    return {"count": len(out), "items": _limit(out, limit)}


def tool_run_tender_hunter(sources=None, recent_days=0, limit=0):
    """Run Agent 1 (Tender Hunter): scrape, analyze and score tenders."""
    return runner.run_tenders(sources=_as_list(sources), recent_days=_as_int(recent_days), limit=_as_int(limit))


def tool_run_partner_scout(source=None, countries=None, limit=0):
    """Run Agent 2 (Partner Scout): find and qualify local IT partners."""
    return runner.run_partners(source=source, countries=_as_list(countries), limit=_as_int(limit))


def tool_run_event_mapper(source=None, upcoming_days=0, limit=0):
    """Run Agent 3 (Event Mapper): map events and profile leads."""
    return runner.run_events(source=source, upcoming_days=_as_int(upcoming_days), limit=_as_int(limit))


def tool_save_item(kind, item_id):
    """Bookmark a result for later review (kind: tenders | partners | leads)."""
    return saved.save_item(kind, item_id)


def tool_help():
    """Explain what the assistant can do."""
    return {
        "message": (
            "Je peux : résumer l'état des agents ; chercher des appels d'offres "
            "(tenders), partenaires et leads avec filtres (pays, score, date) ; "
            "lancer un agent (ex. scanner les appels d'offres récents) ; et "
            "enregistrer un résultat dans les favoris. Répondez-moi en "
            "français, anglais ou arabe."
        ),
        "tools": [
            "dashboard_summary",
            "search_tenders(query, country, min_score, recent_days, limit)",
            "search_partners(query, country, min_score, limit)",
            "search_leads(query, country, min_score, priority, limit)",
            "run_tender_hunter(sources, recent_days, limit)",
            "run_partner_scout(source, countries, limit)",
            "run_event_mapper(source, upcoming_days, limit)",
            "save_item(kind, item_id)",
        ],
    }


TOOLS: dict[str, callable] = {
    "dashboard_summary": tool_dashboard_summary,
    "search_tenders": tool_search_tenders,
    "search_partners": tool_search_partners,
    "search_leads": tool_search_leads,
    "run_tender_hunter": tool_run_tender_hunter,
    "run_partner_scout": tool_run_partner_scout,
    "run_event_mapper": tool_run_event_mapper,
    "save_item": tool_save_item,
    "help": tool_help,
}
