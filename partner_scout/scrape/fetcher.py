"""Company website fetcher (Task 3.2).

Fetches the homepage, discovers the most relevant pages (Case Studies,
References, Partners, About, Contact, Services) and returns their extracted
text. In sample mode the company already carries its pages; they are used as-is.
"""

from __future__ import annotations

import logging
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from partner_scout import config
from partner_scout.models import ESNCompany, PageText
from partner_scout.scrape.extract import classify_page, html_title, html_to_text, is_fetchable

log = logging.getLogger(__name__)

_WANTED_KINDS = ("case_studies", "references", "partners", "work", "services", "about", "contact")


def fetch_company_pages(
    company: ESNCompany,
    max_pages: int | None = None,
    proxy: dict | None = None,
) -> list[PageText]:
    """Return the pages to analyze for a company (offline corpus or live fetch)."""
    max_pages = max_pages or config.MAX_PAGES_PER_COMPANY

    if company.pages:
        return list(company.pages)[:max_pages]

    home = _fetch_page(company.website, proxy)
    if home is None:
        return []

    pages: list[PageText] = [home]
    found_kinds: set[str] = {home.kind}

    links = _discover_links(company.website, home.url)
    for url, anchor_text in links:
        if len(pages) >= max_pages:
            break
        if url in {p.url for p in pages}:
            continue
        kind = classify_page(url, anchor_text)
        if kind == "unknown":
            continue
        # Only fetch pages that add a kind we still need (or are home variants).
        if kind in found_kinds and kind not in ("contact", "about"):
            continue
        page = _fetch_page(url, proxy)
        if page is None or not page.text:
            continue
        pages.append(page)
        found_kinds.add(kind)

    log.info("[%s] fetched %d page(s)", company.id, len(pages))
    return pages[:max_pages]


def _fetch_page(url: str, proxy: dict | None) -> PageText | None:
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": config.USER_AGENT, "Accept": "text/html,*/*"},
            timeout=config.HTTP_TIMEOUT,
            proxies=proxy,
        )
        resp.raise_for_status()
        if "text/html" not in (resp.headers.get("content-type", "") or "") and not resp.text.lstrip().startswith("<"):
            return None
    except Exception as exc:  # noqa: BLE001 - best-effort fetch
        log.warning("fetch failed for %s: %s", url, exc.__class__.__name__)
        return None

    text = html_to_text(resp.text, config.MAX_PAGE_TEXT_CHARS)
    if len(text) < config.MIN_PAGE_TEXT_CHARS:
        return None
    kind = classify_page(resp.url or url)
    if kind == "unknown":
        kind = classify_page(url)
    return PageText(url=resp.url or url, title=html_title(resp.text), kind=kind, text=text)


def _discover_links(site_root: str, home_url: str, limit: int = 60) -> list[tuple[str, str]]:
    """Collect same-domain candidate links (href, anchor text) from the homepage."""
    try:
        resp = requests.get(
            home_url,
            headers={"User-Agent": config.USER_AGENT, "Accept": "text/html,*/*"},
            timeout=config.HTTP_TIMEOUT,
        )
        resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        log.warning("homepage scan failed for %s: %s", home_url, exc.__class__.__name__)
        return []

    root_domain = urlparse(site_root).netloc.lower().lstrip("www.")
    soup = BeautifulSoup(resp.text, "lxml")
    links: list[tuple[str, str]] = []
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        text = anchor.get_text(" ", strip=True)
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        absolute = urljoin(home_url, href)
        if not is_fetchable(absolute):
            continue
        domain = urlparse(absolute).netloc.lower().lstrip("www.")
        if domain and root_domain and domain != root_domain:
            continue
        links.append((absolute, text[:120]))
        if len(links) >= limit:
            break
    return links
