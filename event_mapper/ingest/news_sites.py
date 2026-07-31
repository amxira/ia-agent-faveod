"""Regional IT news-site adapter (Task 4.1): TechCabal, ArabianBusiness.

We scan the sites' technology category pages for article titles mentioning an
event keyword and treat those articles as event announcements. Best-effort and
degrade to [] when unreachable.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from event_mapper.ingest.base import EventSource, get_with_fallback
from event_mapper.models import ITEvent
from tender_hunter.ingest.proxy import ProxyProvider

log = logging.getLogger(__name__)

FEEDS = {
    "techcabal": "https://techcabal.com/",
    "arabian_business": "https://www.arabianbusiness.com/technology",
}


class NewsSource(EventSource):
    name = "news"

    def fetch(self, countries, keywords, proxy: ProxyProvider | None = None) -> list[ITEvent]:
        events: list[ITEvent] = []
        seen: set[str] = set()
        for site, url in FEEDS.items():
            try:
                resp = get_with_fallback(url, proxy)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "lxml")
            except Exception as exc:  # noqa: BLE001 - best-effort source
                log.warning("[news] %s failed: %s", site, exc.__class__.__name__)
                continue

            for anchor in soup.find_all("a", href=True):
                title = re.sub(r"\s+", " ", anchor.get_text(" ", strip=True)).strip()
                if len(title) < 15:
                    continue
                lower = title.lower()
                matched = [k for k in keywords if k.lower() in lower]
                eventy = any(w in lower for w in ("summit", "conference", "forum", "congress", "expo"))
                if not matched or not eventy:
                    continue
                href = urljoin(url, anchor.get("href", ""))
                if href in seen:
                    continue
                seen.add(href)
                events.append(
                    ITEvent(
                        id=f"NW-{len(events):03d}",
                        name=title[:200],
                        source=f"news:{site}",
                        url=href,
                        description=f"Event announcement published on {site}.",
                        keywords_matched=matched,
                        raw={"site": site},
                    )
                )
        log.info("[news] parsed %d event(s)", len(events))
        return events
