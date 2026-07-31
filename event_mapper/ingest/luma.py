"""Luma adapter (Task 4.1).

Luma (lu.ma) is almost fully client-rendered; we best-effort parse any
server-embedded JSON-LD event blocks and degrade to [] otherwise.
"""

from __future__ import annotations

import logging

from event_mapper.ingest.base import EventSource, event_url_from_json_ld, get_with_fallback, parse_json_ld
from event_mapper.models import ITEvent
from tender_hunter.ingest.proxy import ProxyProvider

log = logging.getLogger(__name__)

CALENDAR_URL = "https://lu.ma/calendar"


class LumaSource(EventSource):
    name = "luma"

    def fetch(self, countries, keywords, proxy: ProxyProvider | None = None) -> list[ITEvent]:
        events: list[ITEvent] = []
        seen: set[str] = set()
        try:
            resp = get_with_fallback(CALENDAR_URL, proxy, params={"locale": "en"})
            resp.raise_for_status()
            blocks = parse_json_ld(resp.text)
        except Exception as exc:  # noqa: BLE001 - best-effort source
            log.warning("[luma] calendar fetch failed: %s", exc.__class__.__name__)
            return []

        for block in blocks:
            name = str(block.get("name") or "").strip()
            url = event_url_from_json_ld(block)
            if not name or not url or url in seen:
                continue
            seen.add(url)
            text = f"{name} {block.get('description') or ''}".lower()
            matched = [k for k in keywords if k.lower() in text]
            if not matched:
                continue
            events.append(
                ITEvent(
                    id=f"LU-{len(events):03d}",
                    name=name[:200],
                    source=self.name,
                    url=url,
                    start_date=str(block.get("startDate") or ""),
                    description=str(block.get("description") or "")[:500],
                    keywords_matched=matched,
                )
            )
        log.info("[luma] parsed %d event(s)", len(events))
        return events
