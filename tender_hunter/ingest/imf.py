"""IMF source.

The IMF procurement portal blocks simple clients (403 observed in dev).
The adapter stays live-ready; it is expected to return [] until residential
proxies or the operator's network allow access. A note is logged each run.
"""

from __future__ import annotations

import logging
import re

from bs4 import BeautifulSoup

from tender_hunter.ingest.base import TenderSource, get_with_fallback
from tender_hunter.ingest.proxy import ProxyProvider
from tender_hunter.models import Tender

log = logging.getLogger(__name__)

PORTAL_URLS = [
    "https://www.imf.org/en/About/Procurement",
    "https://www.imf.org/external/np/procure/eng/index.htm",
]


class IMFSource(TenderSource):
    name = "imf"

    def fetch(self, proxy: ProxyProvider | None = None) -> list[Tender]:
        tenders: list[Tender] = []
        seen: set[str] = set()
        for url in PORTAL_URLS:
            try:
                resp = get_with_fallback(url, proxy)
                resp.raise_for_status()
            except Exception as exc:  # noqa: BLE001
                log.warning("[imf] fetch %s failed: %s", url, exc)
                continue

            soup = BeautifulSoup(resp.text, "lxml")
            for anchor in soup.find_all("a", href=True):
                text = re.sub(r"\s+", " ", anchor.get_text(" ", strip=True))
                href = anchor["href"]
                if not re.search(r"procure|tender|opportunit|rfp|request.?for", href, re.I):
                    continue
                if not text or len(text) < 12 or href in seen:
                    continue
                seen.add(href)
                full = href if href.startswith("http") else f"https://www.imf.org{href}"
                tenders.append(
                    Tender(
                        id=f"IMF-{len(seen):04d}",
                        source="imf",
                        title=text[:200],
                        agency="International Monetary Fund",
                        description=f"IMF procurement notice. Link: {full}",
                        url=full,
                        language="en",
                        raw={"href": full},
                    )
                )
        log.info("[imf] parsed %d notice link(s)", len(tenders))
        return tenders
