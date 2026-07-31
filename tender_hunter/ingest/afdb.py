"""AfDB source.

The AfDB procurement portal is frequently slow/geo-restricted from foreign IPs.
The adapter is live-ready: it fetches the procurement opportunities pages and
parses links. When the network or the portal blocks us it returns [] and the
pipeline continues on the other sources. Rotating residential proxies are the
production fix (see ingest/proxy.py).
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
    "https://www.afdb.org/en/procurement/opportunities",
    "https://www.afdb.org/en/projects-procurement",
]


class AfDBSource(TenderSource):
    name = "afdb"

    def fetch(self, proxy: ProxyProvider | None = None) -> list[Tender]:
        tenders: list[Tender] = []
        seen: set[str] = set()
        for url in PORTAL_URLS:
            try:
                resp = get_with_fallback(url, proxy, timeout=45)
                resp.raise_for_status()
            except Exception as exc:  # noqa: BLE001
                log.warning("[afdb] fetch %s failed: %s", url, exc)
                continue

            soup = BeautifulSoup(resp.text, "lxml")
            for anchor in soup.find_all("a", href=True):
                text = re.sub(r"\s+", " ", anchor.get_text(" ", strip=True))
                href = anchor["href"]
                if not re.search(r"procurement|notice|opportunit|tender|bidding|consultanc", href, re.I):
                    continue
                if not text or len(text) < 12 or href in seen:
                    continue
                seen.add(href)
                full = href if href.startswith("http") else f"https://www.afdb.org{href}"
                tenders.append(
                    Tender(
                        id=f"AFDB-{len(seen):04d}",
                        source="afdb",
                        title=text[:200],
                        agency="African Development Bank",
                        region="Africa",
                        description=f"AfDB procurement opportunity. Link: {full}",
                        url=full,
                        language="en",
                        raw={"href": full},
                    )
                )
        log.info("[afdb] parsed %d opportunity link(s)", len(tenders))
        return tenders
