"""Source registry: maps configured source names to adapters and runs them."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from tender_hunter import config
from tender_hunter.ingest.afdb import AfDBSource
from tender_hunter.ingest.base import TenderSource
from tender_hunter.ingest.ebrd import EBRDSource
from tender_hunter.ingest.imf import IMFSource
from tender_hunter.ingest.proxy import ProxyProvider
from tender_hunter.ingest.sample_data import build_sample_tenders
from tender_hunter.ingest.world_bank import WorldBankSource
from tender_hunter.models import Tender

log = logging.getLogger(__name__)

AVAILABLE_SOURCES: dict[str, type[TenderSource]] = {
    "world_bank": WorldBankSource,
    "ebrd": EBRDSource,
    "afdb": AfDBSource,
    "imf": IMFSource,
}


def _sample_tenders() -> list[Tender]:
    return [Tender.model_validate(raw) for raw in build_sample_tenders()]


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


def _recent(tenders: list[Tender], days: int) -> list[Tender]:
    """Keep only tenders published (or with a deadline) within the last N days.

    Tenders without a parseable date are dropped when the filter is active -
    their recency cannot be verified.
    """
    if not days or days <= 0:
        return tenders
    cutoff = datetime.utcnow() - timedelta(days=days)
    kept: list[Tender] = []
    for tender in tenders:
        date = _parse_date(tender.publication_date) or _parse_date(tender.deadline)
        if date is not None and date >= cutoff:
            kept.append(tender)
    log.info("recent filter: %d -> %d tender(s) within last %d day(s)", len(tenders), len(kept), days)
    return kept


def fetch_all(source_names: list[str], proxy: ProxyProvider | None = None) -> list[Tender]:
    """Fetch tenders from the requested sources.

    Each adapter is best-effort and never raises. If no live source returns
    data, the sample dataset is added so the pipeline still runs end-to-end.
    The configured RECENT_DAYS filter (0 = off) is applied before returning.
    """
    tenders: list[Tender] = []
    names = source_names or ["sample"]

    for name in names:
        if name == "sample":
            sample = _sample_tenders()
            log.info("[sample] generated %d sample tender(s)", len(sample))
            tenders.extend(sample)
            continue
        if name not in AVAILABLE_SOURCES:
            log.warning("unknown source %r (available: %s)", name, ", ".join(list(AVAILABLE_SOURCES) + ["sample"]))
            continue
        try:
            fetched = AVAILABLE_SOURCES[name]().fetch(proxy)
        except Exception as exc:  # noqa: BLE001 - registry must stay resilient
            log.warning("[%s] adapter crashed: %s", name, exc)
            fetched = []
        if len(fetched) > config.MAX_PER_SOURCE:
            log.info("[%s] trimming %d -> %d (MAX_PER_SOURCE)", name, len(fetched), config.MAX_PER_SOURCE)
            fetched = fetched[: config.MAX_PER_SOURCE]
        tenders.extend(fetched)

    if not any(t.source == "sample" for t in tenders) and not tenders:
        log.warning("no tenders fetched from any source; seeding sample dataset")
        tenders = _sample_tenders()

    return _recent(tenders, config.RECENT_DAYS)
