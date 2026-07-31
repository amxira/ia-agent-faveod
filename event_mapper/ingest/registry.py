"""Event source registry: maps configured backend names to adapters and runs them."""

from __future__ import annotations

import logging

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
    """Fetch events from the requested backend; seed sample data if empty."""
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
    return events[: config.MAX_EVENTS]


class _SampleSource(EventSource):
    """Offline backend: returns the built-in sample event corpus."""

    name = "sample"

    def fetch(self, countries, keywords, proxy=None) -> list[ITEvent]:
        events = build_sample_events()
        log.info("[sample] generated %d sample event(s)", len(events))
        return events
