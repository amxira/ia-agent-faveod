"""Event website fetcher (Task 4.2).

Fetches the event homepage and discovers the most relevant pages (Speakers,
Agenda, Attendees) to feed the NER extraction. In sample mode the event already
carries its pages; they are used as-is.
"""

from __future__ import annotations

import logging
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from event_mapper import config
from event_mapper.models import ITEvent, PageText
from event_mapper.scrape.extract import classify_page, html_title, html_to_text, is_fetchable
from tender_hunter import config as shared_config

log = logging.getLogger(__name__)

_WANTED_KINDS = ("speakers", "agenda", "attendees", "about")


def fetch_event_pages(event: ITEvent, max_pages: int | None = None, proxy: dict | None = None) -> list[PageText]:
    max_pages = max_pages or config.MAX_PAGES_PER_EVENT

    if event.pages:
        return list(event.pages)[:max_pages]

    home = _fetch_page(event.url, proxy)
    if home is None:
        return []

    pages: list[PageText] = [home]
    found_kinds: set[str] = {home.kind}

    links = _discover_links(event.url, home.url)
    for url, anchor_text in links:
        if len(pages) >= max_pages:
            break
        if url in {p.url for p in pages}:
            continue
        kind = classify_page(url, anchor_text)
        if kind == "unknown" or kind in found_kinds:
            continue
        page = _fetch_page(url, proxy)
        if page is None or not page.text:
            continue
        pages.append(page)
        found_kinds.add(kind)

    log.info("[%s] fetched %d page(s)", event.id, len(pages))
    return pages[:max_pages]


def _fetch_page(url: str, proxy: dict | None) -> PageText | None:
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": shared_config.USER_AGENT, "Accept": "text/html,*/*"},
            timeout=config.EVENT_FETCH_TIMEOUT,
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
    try:
        resp = requests.get(
            home_url,
            headers={"User-Agent": shared_config.USER_AGENT, "Accept": "text/html,*/*"},
            timeout=config.EVENT_FETCH_TIMEOUT,
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
