"""Search engine registry: maps configured backend names to engines and runs them."""

from __future__ import annotations

import logging

from partner_scout import config
from partner_scout.models import ESNCompany
from partner_scout.search.base import SearchEngine
from partner_scout.search.sample_data import build_sample_companies
from partner_scout.search.searxng import SearXNGEngine

log = logging.getLogger(__name__)

AVAILABLE_ENGINES: dict[str, type[SearchEngine]] = {
    "searxng": SearXNGEngine,
}


def get_search_engine(name: str | None = None) -> SearchEngine:
    name = (name or config.SEARCH_SOURCE).strip().lower()
    if name == "sample":
        return _SampleEngine()
    if name not in AVAILABLE_ENGINES:
        log.warning(
            "unknown search backend %r (available: %s); falling back to sample",
            name,
            ", ".join(list(AVAILABLE_ENGINES) + ["sample"]),
        )
        return _SampleEngine()
    return AVAILABLE_ENGINES[name]()


def run_search(
    countries: list[str] | None = None,
    terms: list[str] | None = None,
    engine: SearchEngine | None = None,
) -> list[ESNCompany]:
    """Discover companies from the configured backend; seed sample data if empty."""
    engine = engine or get_search_engine()
    countries = countries or config.TARGET_COUNTRIES
    terms = terms or config.SEARCH_TERMS

    companies = []
    try:
        companies = engine.search(countries, terms)
    except Exception as exc:  # noqa: BLE001 - registry must stay resilient
        log.warning("[%s] search crashed: %s", engine.name, exc)
        companies = []

    if not companies:
        log.warning("no companies discovered by %r; seeding sample dataset", engine.name)
        companies = build_sample_companies()
    return companies[: config.MAX_COMPANIES]


class _SampleEngine(SearchEngine):
    """Offline backend: returns the built-in sample corpus."""

    name = "sample"

    def search(self, countries: list[str], terms: list[str]) -> list[ESNCompany]:
        companies = build_sample_companies()
        log.info("[sample] generated %d sample company(ies)", len(companies))
        return companies
