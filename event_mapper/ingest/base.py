"""Event source base class + shared helpers for the event scraping engine."""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from urllib.parse import urljoin

import requests

from event_mapper import config
from event_mapper.models import ITEvent
from tender_hunter.ingest.proxy import ProxyProvider

log = logging.getLogger(__name__)


def get_with_fallback(
    url: str,
    proxy: ProxyProvider | None,
    params: dict | None = None,
    timeout: int | None = None,
) -> requests.Response:
    """GET a URL through the proxy, retrying direct once on proxy failure."""
    headers = {"User-Agent": config.USER_AGENT, "Accept": "*/*"}
    timeout = timeout or config.EVENT_FETCH_TIMEOUT
    proxies = proxy.get_proxy() if proxy else None
    try:
        return requests.get(url, params=params, headers=headers, timeout=timeout, proxies=proxies)
    except requests.RequestException as exc:
        if proxies is None:
            raise
        log.warning("Proxy %s failed for %s (%s); retrying direct", proxies, url, exc.__class__.__name__)
        return requests.get(url, params=params, headers=headers, timeout=timeout)


def parse_json_ld(html: str) -> list[dict]:
    """Extract schema.org JSON-LD event objects from an HTML page."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")
    events: list[dict] = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or script.get_text())
        except (json.JSONDecodeError, TypeError):
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            if item.get("@type") == "Event" or (item.get("@type") and isinstance(item.get("@type"), list) and "Event" in item["@type"]):
                events.append(item)
            if "@graph" in item and isinstance(item["@graph"], list):
                for sub in item["@graph"]:
                    if isinstance(sub, dict) and sub.get("@type") == "Event":
                        events.append(sub)
    return events


def event_url_from_json_ld(event: dict) -> str:
    return str(event.get("url") or "")


class EventSource(ABC):
    """One event-platform adapter. Best-effort: never raise."""

    name: str = "base"

    @abstractmethod
    def fetch(self, countries: list[str], keywords: list[str], proxy: ProxyProvider | None = None) -> list[ITEvent]:
        """Fetch events from this platform. Return [] on any failure."""

    def __str__(self) -> str:  # pragma: no cover - debug helper
        return self.name
