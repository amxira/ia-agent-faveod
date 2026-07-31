"""Source base class + shared HTTP helper for the scraping engine."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

import requests

from tender_hunter import config
from tender_hunter.ingest.proxy import ProxyProvider
from tender_hunter.models import Tender

log = logging.getLogger(__name__)


def get_with_fallback(
    url: str,
    proxy: ProxyProvider,
    params: dict | None = None,
    timeout: int | None = None,
) -> requests.Response:
    """GET a URL through the proxy, retrying direct once on proxy failure.

    Raises the original exception if the direct retry also fails, or if no proxy
    is configured (so callers can catch and degrade gracefully).
    """
    headers = {"User-Agent": config.USER_AGENT, "Accept": "*/*"}
    timeout = timeout or config.HTTP_TIMEOUT

    proxies = proxy.get_proxy() if proxy else None
    try:
        return requests.get(url, params=params, headers=headers, timeout=timeout, proxies=proxies)
    except requests.RequestException as exc:
        if proxies is None:
            raise
        log.warning("Proxy %s failed for %s (%s); retrying direct", proxies, url, exc.__class__.__name__)
        return requests.get(url, params=params, headers=headers, timeout=timeout)


class TenderSource(ABC):
    """One tender portal adapter. Best-effort: never raise."""

    name: str = "base"

    @abstractmethod
    def fetch(self, proxy: ProxyProvider | None = None) -> list[Tender]:
        """Fetch tenders from this portal. Return [] on any failure."""

    def __str__(self) -> str:  # pragma: no cover - debug helper
        return self.name
