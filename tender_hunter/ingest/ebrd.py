"""EBRD source.

EBRD's public notice listing lives on the ECEPP e-procurement portal, which
server-renders the full notice table (~3-4 MB HTML). We parse each notice row:
title, notice type, closing date, published date, reference, country and
sector. No JS rendering or paid proxy required.
"""

from __future__ import annotations

import logging
import re

from bs4 import BeautifulSoup

from tender_hunter.ingest.base import TenderSource, get_with_fallback
from tender_hunter.ingest.proxy import ProxyProvider
from tender_hunter.models import Tender

log = logging.getLogger(__name__)

NOTICES_URL = "https://ecepp.ebrd.com/delta/noticeSearchResults.html"
_ID_RE = re.compile(r"displayNoticeId=(\d+)")


class EBRDSource(TenderSource):
    name = "ebrd"

    def fetch(self, proxy: ProxyProvider | None = None) -> list[Tender]:
        try:
            resp = get_with_fallback(NOTICES_URL, proxy, timeout=90)
            resp.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            log.warning("[ebrd] fetch failed: %s", exc)
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        tenders: list[Tender] = []
        seen: set[int] = set()
        for anchor in soup.find_all("a", href=True):
            href = anchor.get("href") or ""
            match = _ID_RE.search(href)
            if not match:
                continue
            notice_id = int(match.group(1))
            if notice_id in seen:
                continue
            seen.add(notice_id)

            row = anchor.find_parent("tr")
            cells = [re.sub(r"\s+", " ", td.get_text(" ", strip=True)).strip() for td in row.find_all("td")] if row else []

            def cell(i: int) -> str:
                return cells[i] if len(cells) > i else ""

            meta = [m.strip() for m in cell(9).split(",")] if len(cell(9)) > 2 else []
            country = meta[2] if len(meta) > 2 else ""
            client = meta[4] if len(meta) > 4 else ""
            sector = meta[5] if len(meta) > 5 else ""

            closing = cell(3).split("UK Time")[0].strip()
            tenders.append(
                Tender(
                    id=f"EBRD-{notice_id}",
                    source="ebrd",
                    title=re.sub(r"\s+", " ", anchor.get_text(" ", strip=True)),
                    country=country,
                    agency="EBRD",
                    description=(
                        f"EBRD {cell(1) or 'notice'}"
                        + (f" - sector: {sector}" if sector else "")
                        + (f" - client: {client}" if client else "")
                    ),
                    reference=cell(7),
                    deadline=closing or None,
                    publication_date=cell(6) or None,
                    url=f"https://ecepp.ebrd.com/delta/viewNotice.html?displayNoticeId={notice_id}",
                    language="en",
                    raw={"notice_type": cell(1), "state": cell(5), "sector": sector, "client": client},
                )
            )
        log.info("[ebrd] parsed %d notice(s)", len(tenders))
        return tenders
