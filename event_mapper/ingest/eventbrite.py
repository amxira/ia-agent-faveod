"""Eventbrite adapter (Task 4.1).

Eventbrite embeds schema.org JSON-LD events in its search/detail pages; we parse
those blocks. No API token required. Degrades to [] when unreachable.
"""

from __future__ import annotations

import logging
from urllib.parse import quote

from event_mapper.ingest.base import EventSource, event_url_from_json_ld, get_with_fallback, parse_json_ld
from event_mapper.models import ITEvent
from tender_hunter.ingest.proxy import ProxyProvider

log = logging.getLogger(__name__)

SEARCH_URL = "https://www.eventbrite.com/d/{region}/tech--events/"


class EventbriteSource(EventSource):
    name = "eventbrite"

    def fetch(self, countries, keywords, proxy: ProxyProvider | None = None) -> list[ITEvent]:
        events: list[ITEvent] = []
        seen: set[str] = set()
        region = countries[0].lower().replace(" ", "-") if countries else "international"

        for keyword in keywords:
            try:
                resp = get_with_fallback(
                    SEARCH_URL.format(region=region),
                    proxy,
                    params={"q": quote(keyword)},
                )
                resp.raise_for_status()
                blocks = parse_json_ld(resp.text)
            except Exception as exc:  # noqa: BLE001 - best-effort source
                log.warning("[eventbrite] query %r failed: %s", keyword, exc.__class__.__name__)
                continue

            for block in blocks:
                name = str(block.get("name") or "").strip()
                url = event_url_from_json_ld(block)
                if not name or not url or url in seen:
                    continue
                seen.add(url)
                location = block.get("location") or {}
                city = ""
                if isinstance(location, dict):
                    city = str(location.get("address", {}).get("addressLocality") or "") if isinstance(location.get("address"), dict) else ""
                start = str(block.get("startDate") or "")
                description = str(block.get("description") or "")[:500]
                events.append(
                    ITEvent(
                        id=f"EB-{len(events):03d}",
                        name=name[:200],
                        source=self.name,
                        country=countries[0] if countries else "",
                        city=city,
                        url=url,
                        start_date=start,
                        description=description,
                        keywords_matched=[keyword],
                    )
                )
        log.info("[eventbrite] parsed %d event(s)", len(events))
        return events
