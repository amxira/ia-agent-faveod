"""Rotating proxy middleware.

In dev no paid residential proxy is required. A free list can be provided via
`PROXY_LIST` (comma separated `scheme://host:port`). Requests rotate through the
pool round-robin and transparently retry *direct* when a proxy fails, so the
pipeline never hard-depends on proxy availability.

To swap in a residential service later, implement `ProxyProvider` with your
provider's credential/rotation logic and set it in `make_proxy_provider()`.
"""

from __future__ import annotations

import itertools
import logging
from abc import ABC, abstractmethod

from tender_hunter import config

log = logging.getLogger(__name__)


class ProxyProvider(ABC):
    """Abstract rotating-proxy provider."""

    @abstractmethod
    def get_proxy(self) -> dict | None:
        """Return a requests-style proxies dict (e.g. {"http": ..., "https": ...}) or None."""


class NoProxy(ProxyProvider):
    def get_proxy(self) -> dict | None:  # noqa: D102
        return None


class RotatingProxyPool(ProxyProvider):
    """Round-robin pool over a static list of proxies."""

    def __init__(self, proxy_list: list[str]):
        self._pool = itertools.cycle(proxy_list)
        self._size = len(proxy_list)

    def get_proxy(self) -> dict | None:  # noqa: D102
        if self._size == 0:
            return None
        proxy = next(self._pool)
        return {"http": proxy, "https": proxy}


def make_proxy_provider() -> ProxyProvider:
    if not config.PROXY_LIST:
        return NoProxy()
    log.info("Rotating proxy pool active with %d proxies", len(config.PROXY_LIST))
    return RotatingProxyPool(config.PROXY_LIST)
