"""Embedder interface + cosine helpers."""

from __future__ import annotations

import math
from abc import ABC, abstractmethod


class Embedder(ABC):
    """Produces L2-normalized dense vectors for chunks/queries."""

    dimension: int

    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts (can be 1)."""

    def embed(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]


def l2_normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0:
        return vec
    return [v / norm for v in vec]


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    return float(sum(x * y for x, y in zip(a, b)))
