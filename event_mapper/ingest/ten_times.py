"""10times adapter (Task 4.1).

10times is a global trade-show calendar. Its search results are mostly rendered
client-side; we best-effort parse server-rendered anchors / JSON-LD and degrade
to [] when the page is unreachable or JS-only.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import quote

from bs4 import BeautifulSoup

from event_mapper.ingest.base import EventSource, get_with_fallback
from event_mapper.models import ITEvent
from tender_hunter.ingest.proxy import ProxyProvider

log = logging.getLogger(__name__)

SEARCH_URL = "https://www.10times.com/search"
_ID_RE = re.compile(r"([A-Za-z0-9\-]+)-([0-9a-f]{8,})")


class TenTimesSource(EventSource):
    name = "ten_times"

    def fetch(self, countries, keywords, proxy: ProxyProvider | None = None) -> list[ITEvent]:
        events: list[ITEvent] = []
        seen: set[str] = set()
        for keyword in keywords:
            try:
                resp = get_with_fallback(
                    SEARCH_URL,
                    proxy,
                    params={"q": quote(f"{keyword} technology")},
                )
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "lxml")
            except Exception as exc:  # noqa: BLE001 - best-effort source
                log.warning("[ten_times] query %r failed: %s", keyword, exc.__class__.__name__)
                continue

            for anchor in soup.find_all("a", href=True):
                href = anchor.get("href", "")
                text = re.sub(r"\s+", " ", anchor.get_text(" ", strip=True)).strip()
                if len(text) < 8 or not text.lower().endswith(("expo", "conference", "summit", "show", "fair")):
                    continue
                if not href.startswith(("/", "http")):
                    continue
                url = href if href.startswith("http") else f"https://www.10times.com{href}"
                if url in seen:
                    continue
                seen.add(url)
                events.append(
                    ITEvent(
                        id=f"10X-{len(events):03d}",
                        name=text[:200],
                        source=self.name,
                        url=url,
                        description=f"Found via 10times search for '{keyword}'.",
                        keywords_matched=[keyword],
                    )
                )
        log.info("[ten_times] parsed %d event(s)", len(events))
        return events
