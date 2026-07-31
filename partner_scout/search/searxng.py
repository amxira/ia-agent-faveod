"""SearXNG search backend (Task 3.1).

Talks to a self-hosted SearXNG instance through its JSON API
(`/search?q=...&format=json`). The instance must enable the `json` format in its
settings (see docker/searxng/settings.yml). No third-party search API, no paid
keys: the meta-search runs fully on our own infrastructure (sovereign).
"""

from __future__ import annotations

import logging
import re
from urllib.parse import urljoin, urlparse

import requests

from partner_scout import config
from partner_scout.models import ESNCompany
from partner_scout.search.base import SearchEngine

log = logging.getLogger(__name__)

# Results we never want as partner candidates.
_SKIP_DOMAINS = {
    "facebook.com", "www.facebook.com", "linkedin.com", "www.linkedin.com",
    "twitter.com", "x.com", "instagram.com", "youtube.com", "youtu.be",
    "github.com", "gitlab.com", "wikipedia.org", "www.wikipedia.org",
    "google.com", "bing.com", "yahoo.com", "duckduckgo.com", "searxng.org",
    "crunchbase.com", "zoominfo.com", "g2.com", "clutch.co", "upwork.com",
}
_TITLE_CLEAN = re.compile(r"\s*[-|]\s*(Software Engineering|Systems Integrator|IT Services).*$", re.I)


class SearXNGEngine(SearchEngine):
    name = "searxng"

    def __init__(self, url: str | None = None):
        self.url = (url or config.SEARXNG_URL).rstrip("/")

    def search(self, countries: list[str], terms: list[str]) -> list[ESNCompany]:
        companies: list[ESNCompany] = []
        seen_domains: set[str] = set()
        seen_ids: set[str] = set()
        headers = {"User-Agent": config.USER_AGENT}

        for country in countries:
            for term in terms:
                query = f'"{term}" {country}'
                try:
                    resp = requests.get(
                        f"{self.url}/search",
                        params={"q": query, "format": "json", "language": "auto"},
                        headers=headers,
                        timeout=config.SEARXNG_TIMEOUT,
                    )
                    resp.raise_for_status()
                    results = resp.json().get("results", [])
                except Exception as exc:  # noqa: BLE001 - best-effort search
                    log.warning("[searxng] query %r failed: %s", query, exc.__class__.__name__)
                    continue

                for result in results:
                    url = str(result.get("url", "") or "")
                    parsed = urlparse(url)
                    if parsed.scheme not in ("http", "https"):
                        continue
                    domain = parsed.netloc.lower()
                    if any(parsed.path.lower().endswith(ext) for ext in (".pdf", ".doc", ".docx", ".xls", ".jpg", ".png")):
                        continue
                    if domain in _SKIP_DOMAINS or any(domain.endswith(skip.lstrip("www.")) for skip in _SKIP_DOMAINS):
                        continue
                    if domain in seen_domains:
                        continue

                    title = re.sub(_TITLE_CLEAN, "", str(result.get("title", ""))).strip()
                    if not title:
                        continue

                    seen_domains.add(domain)
                    cid = f"ES-{abs(hash(url)) % 10**9:09d}"
                    if cid in seen_ids:
                        continue
                    seen_ids.add(cid)
                    companies.append(
                        ESNCompany(
                            id=cid,
                            name=title[:120],
                            country=country,
                            website=url,
                            source="searxng",
                            search_query=query,
                            description=str(result.get("content", ""))[:500],
                            raw={"domain": domain, "engine": str(result.get("engine", ""))},
                        )
                    )

                if len(companies) >= config.MAX_COMPANIES:
                    break
            if len(companies) >= config.MAX_COMPANIES:
                break

        log.info("[searxng] discovered %d candidate company(ies)", len(companies))
        return companies[: config.MAX_COMPANIES]
