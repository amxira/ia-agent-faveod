"""Search engine interface (Task 3.1)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from partner_scout.models import ESNCompany


class SearchEngine(ABC):
    """Discovers local IT companies. Best-effort: never raise."""

    name: str = "base"

    @abstractmethod
    def search(self, countries: list[str], terms: list[str]) -> list[ESNCompany]:
        """Return candidate companies. Return [] on any failure."""
