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
from chat.external_tools import (
    tool_list_tender_portals,
    tool_search_external_tenders,
    tool_search_esn_partners,
    tool_tender_portals_summary,
)

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


# Words that describe the request, not the data - stripped before matching so a
# question like "best events" does not filter every record out.
_META_WORDS = {
    "le", "la", "les", "un", "une", "des", "du", "de", "et", "ou", "au", "aux",
    "en", "dans", "sur", "avec", "pour", "par", "à", "the", "a", "an", "of",
    "to", "for", "in", "and", "with",
    "meilleur", "meilleure", "meilleurs", "meilleures", "mieux", "best", "top",
    "chaque", "each", "per", "tout", "tous", "toutes", "all",
    "donne", "donner", "show", "give", "moi", "je", "veux", "s'il", "sil",
    "vous", "plait", "plaît", "please", "svp",
    "cherche", "chercher", "trouve", "trouver", "recherche", "find", "search",
    "event", "events", "événement", "événements", "evenement", "evenements",
    "conference", "conférence", "summit", "agenda", "programme",
    "tender", "tenders", "appel", "appels", "offre", "offres", "appel_d_offres",
    "partenaire", "partenaires", "partner", "partners", "entreprise", "société",
    "lead", "leads", "prospect", "prospects",
    "récent", "recent", "récents", "recents", "dernier", "derniers", "dernière",
    "pays", "country", "countries", "quel", "quelle", "quels", "quelles", "what", "which",
}


def _clean_query(query) -> str:
    if not query:
        return ""
    words = [w.strip("'\".,!?;:()") for w in str(query).lower().split()]
    return " ".join(w for w in words if w and w not in _META_WORDS)


def _best_per_country(items: list[dict]) -> list[dict]:
    """Keep the first (highest-ranked) item per country; input must be sorted."""
    seen: set[str] = set()
    out: list[dict] = []
    for item in items:
        country = str(item.get("country") or "Autre")
        if country not in seen:
            seen.add(country)
            out.append(item)
    return out


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


def tool_search_tenders(query=None, country=None, min_score=None, recent_days=None, per_country=False, limit=10):
    """Search the analyzed tender reports."""
    records = store.load_tenders()
    min_score = _as_float(min_score)
    recent_days = _as_int(recent_days)
    q = _clean_query(query)
    out = []
    for rec in records:
        if not _matches(rec, q):
            continue
        if not _country_matches(rec, country):
            continue
        if _as_float(rec.get("fit_score")) < min_score:
            continue
        if not _date_in_window(rec.get("publication_date") or rec.get("deadline"), recent_days):
            continue
        out.append(_compact(rec, ("tender_id", "title", "country", "fit_score", "fit_grade", "deadline", "url")))
    out.sort(key=lambda r: r.get("fit_score") or 0, reverse=True)
    if per_country:
        out = _best_per_country(out)
    return {"count": len(out), "items": _limit(out, limit), "grouped": bool(per_country)}


def tool_search_partners(query=None, country=None, min_score=None, per_country=False, limit=10):
    """Search the discovered partner companies."""
    records = store.load_partners()
    min_score = _as_float(min_score)
    q = _clean_query(query)
    out = []
    for rec in records:
        if not _matches(rec, q):
            continue
        if not _country_matches(rec, country):
            continue
        if _as_float(rec.get("affinity_score")) < min_score:
            continue
        out.append(_compact(rec, ("partner_id", "company_name", "country", "affinity_score", "affinity_grade", "qualified", "website")))
    out.sort(key=lambda r: r.get("affinity_score") or 0, reverse=True)
    if per_country:
        out = _best_per_country(out)
    return {"count": len(out), "items": _limit(out, limit), "grouped": bool(per_country)}


def tool_search_leads(query=None, country=None, min_score=None, priority=None, per_country=False, limit=10):
    """Search the event-derived leads / prospects."""
    records = store.load_leads()
    min_score = _as_float(min_score)
    q = _clean_query(query)
    out = []
    for rec in records:
        if not _matches(rec, q):
            continue
        if not _country_matches(rec, country):
            continue
        if _as_float(rec.get("lead_score")) < min_score:
            continue
        if priority and priority.strip().lower() not in str(rec.get("priority") or "").lower():
            continue
        out.append(_compact(rec, ("lead_id", "person_name", "job_title", "company", "country", "lead_score", "priority", "event_name")))
    out.sort(key=lambda r: r.get("lead_score") or 0, reverse=True)
    if per_country:
        out = _best_per_country(out)
    return {"count": len(out), "items": _limit(out, limit), "grouped": bool(per_country)}


def tool_search_events(query=None, country=None, upcoming_days=None, per_country=False, limit=10):
    """Search the mapped IT events; "best" = most profiled leads, then soonest."""
    records = store.load_events()
    lead_counts: dict[str, int] = {}
    for lead in store.load_leads():
        name = str(lead.get("event_name") or "")
        if name:
            lead_counts[name] = lead_counts.get(name, 0) + 1
    upcoming_days = _as_int(upcoming_days)
    q = _clean_query(query)
    out = []
    for rec in records:
        if not _matches(rec, q):
            continue
        if not _country_matches(rec, country):
            continue
        if upcoming_days and not _date_in_window(rec.get("start_date"), upcoming_days):
            continue
        item = _compact(rec, ("id", "name", "country", "city", "start_date", "end_date", "url"))
        item["lead_count"] = lead_counts.get(str(rec.get("name") or ""), 0)
        out.append(item)
    out.sort(key=lambda r: (-(r.get("lead_count") or 0), r.get("start_date") or ""))
    if per_country:
        out = _best_per_country(out)
    return {"count": len(out), "items": _limit(out, limit), "grouped": bool(per_country)}


def _run_without_logs(fn, *args, **kwargs) -> dict:
    """Run an agent but drop the execution log before showing it to the LLM."""
    result = fn(*args, **kwargs)
    if isinstance(result, dict):
        result.pop("log", None)
    return result


def tool_run_tender_hunter(sources=None, recent_days=0, limit=0):
    """Run Agent 1 (Tender Hunter): scrape, analyze and score tenders."""
    return _run_without_logs(runner.run_tenders, sources=_as_list(sources), recent_days=_as_int(recent_days), limit=_as_int(limit))


def tool_run_partner_scout(source=None, countries=None, limit=0):
    """Run Agent 2 (Partner Scout): find and qualify local IT partners."""
    return _run_without_logs(runner.run_partners, source=source, countries=_as_list(countries), limit=_as_int(limit))


def tool_run_event_mapper(source=None, upcoming_days=0, limit=0):
    """Run Agent 3 (Event Mapper): map events and profile leads."""
    return _run_without_logs(runner.run_events, source=source, upcoming_days=_as_int(upcoming_days), limit=_as_int(limit))


def tool_save_item(kind, item_id):
    """Bookmark a result for later review (kind: tenders | partners | leads)."""
    return saved.save_item(kind, item_id)


def tool_help():
    """Explain what the assistant can do."""
    return {
        "message": (
            "Je peux : résumer l'état des agents ; chercher des appels d'offres "
            "(tenders), partenaires et leads avec filtres (pays, score, date) ; "
            "lancer un agent (ex. scanner les appels d'offres récents) ; "
            "enregistrer un résultat dans les favoris ; "
            "ET rechercher des appels d'offres et des partenaires ESN en "
            "Afrique et au Moyen-Orient sur des portails externes. "
            "Répondez-moi en français, anglais ou arabe."
        ),
        "tools": [
            "dashboard_summary",
            "search_tenders(query, country, min_score, recent_days, per_country, limit)",
            "search_partners(query, country, min_score, per_country, limit)",
            "search_leads(query, country, min_score, priority, per_country, limit)",
            "search_events(query, country, upcoming_days, per_country, limit)",
            "run_tender_hunter(sources, recent_days, limit)",
            "run_partner_scout(source, countries, limit)",
            "run_event_mapper(source, upcoming_days, limit)",
            "save_item(kind, item_id)",
            "--- EXTERNAL SEARCH (Afrique & Moyen-Orient) ---",
            "search_external_tenders(query, zone, limit)",
            "search_esn_partners(country, expertise, groupable_only)",
            "list_tender_portals()",
            "tender_portals_summary()",
        ],
    }


TOOLS: dict[str, callable] = {
    "dashboard_summary": tool_dashboard_summary,
    "search_tenders": tool_search_tenders,
    "search_partners": tool_search_partners,
    "search_leads": tool_search_leads,
    "search_events": tool_search_events,
    "run_tender_hunter": tool_run_tender_hunter,
    "run_partner_scout": tool_run_partner_scout,
    "run_event_mapper": tool_run_event_mapper,
    "save_item": tool_save_item,
    "search_external_tenders": tool_search_external_tenders,
    "search_esn_partners": tool_search_esn_partners,
    "list_tender_portals": tool_list_tender_portals,
    "tender_portals_summary": tool_tender_portals_summary,
    "help": tool_help,
}
