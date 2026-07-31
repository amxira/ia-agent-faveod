"""Event source registry: maps configured backend names to adapters and runs them."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from event_mapper import config
from event_mapper.ingest.base import EventSource
from event_mapper.ingest.eventbrite import EventbriteSource
from event_mapper.ingest.luma import LumaSource
from event_mapper.ingest.news_sites import NewsSource
from event_mapper.ingest.sample_data import build_sample_events
from event_mapper.ingest.ten_times import TenTimesSource
from event_mapper.models import ITEvent
from tender_hunter.ingest.proxy import make_proxy_provider

log = logging.getLogger(__name__)

AVAILABLE_SOURCES: dict[str, type[EventSource]] = {
    "ten_times": TenTimesSource,
    "eventbrite": EventbriteSource,
    "luma": LumaSource,
    "news": NewsSource,
}


def get_event_source(name: str | None = None) -> EventSource:
    name = (name or config.EVENT_SOURCE).strip().lower()
    if name == "sample":
        return _SampleSource()
    if name not in AVAILABLE_SOURCES:
        log.warning(
            "unknown event source %r (available: %s); falling back to sample",
            name,
            ", ".join(list(AVAILABLE_SOURCES) + ["sample"]),
        )
        return _SampleSource()
    return AVAILABLE_SOURCES[name]()


def fetch_all(
    countries: list[str] | None = None,
    keywords: list[str] | None = None,
    source: str | None = None,
) -> list[ITEvent]:
    """Fetch events from the requested backend; seed sample data if empty.

    Applies the configured UPCOMING_DAYS filter (0 = off): only events
    starting within the next N days are kept.
    """
    countries = countries or config.EVENT_COUNTRIES
    keywords = keywords or config.EVENT_KEYWORDS
    engine = get_event_source(source)
    proxy = make_proxy_provider()

    events = []
    try:
        events = engine.fetch(countries, keywords, proxy)
    except Exception as exc:  # noqa: BLE001 - registry must stay resilient
        log.warning("[%s] adapter crashed: %s", engine.name, exc)
        events = []

    if not events:
        log.warning("no events from %r; seeding sample dataset", engine.name)
        events = build_sample_events()
    events = events[: config.MAX_EVENTS]
    return _upcoming(events, config.UPCOMING_DAYS)


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()[:19]
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _upcoming(events: list[ITEvent], days: int) -> list[ITEvent]:
    """Keep only events starting within the next N days.

    Events without a parseable start date are dropped when the filter is
    active - their timing cannot be verified.
    """
    if not days or days <= 0:
        return events
    now = datetime.utcnow()
    horizon = now + timedelta(days=days)
    kept: list[ITEvent] = []
    for event in events:
        date = _parse_date(event.start_date)
        if date is not None and now <= date <= horizon:
            kept.append(event)
    log.info("upcoming filter: %d -> %d event(s) within next %d day(s)", len(events), len(kept), days)
    return kept


class _SampleSource(EventSource):
    """Offline backend: returns the built-in sample event corpus."""

    name = "sample"

    def fetch(self, countries, keywords, proxy=None) -> list[ITEvent]:
        events = build_sample_events()
        log.info("[sample] generated %d sample event(s)", len(events))
        return events
