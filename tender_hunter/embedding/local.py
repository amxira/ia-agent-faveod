"""Zero-dependency lexical embedder (hashing TF-IDF).

Used when no online embedding key is configured or Gemini is unreachable, so
the RAG pipeline and the 0.75 similarity guardrail still function offline.
Vectors live in a fixed-size hashed term space, so query vectors and document
vectors are comparable. Approximate for similarity gating - fine for dev.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections import defaultdict

from tender_hunter.embedding.base import Embedder, l2_normalize


def _tokens(text: str) -> list[str]:
    return [t.lower() for t in re.findall(r"\w+", text or "") if len(t) > 1]


def _features(text: str) -> dict[str, float]:
    """Word unigrams + in-word char trigrams (fastText-style) for fuzzy overlap."""
    feats: dict[str, float] = {}
    for word in _tokens(text):
        feats[f"w:{word}"] = feats.get(f"w:{word}", 0.0) + 1.0
        padded = f"##{word}##"
        for i in range(max(0, len(padded) - 2)):
            gram = padded[i : i + 3]
            feats[f"c:{gram}"] = feats.get(f"c:{gram}", 0.0) + 1.0
    return feats


class LocalEmbedder(Embedder):
    def __init__(self, dimension: int = 768):
        self.dimension = dimension

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        df: dict[str, int] = defaultdict(int)
        feature_lists: list[dict[str, float]] = []
        for text in texts:
            feats = _features(text)
            feature_lists.append(feats)
            for key in feats:
                df[key] += 1

        n_docs = len(feature_lists)
        vectors: list[list[float]] = []
        for feats in feature_lists:
            vec = [0.0] * self.dimension
            for key, freq in feats.items():
                idf = math.log((1 + n_docs) / (1 + df[key])) + 1.0
                weight = 1.0 + math.log(freq)  # sublinear tf
                bucket = int(hashlib.md5(key.encode("utf-8")).hexdigest(), 16) % self.dimension
                vec[bucket] += weight * idf
            vectors.append(l2_normalize(vec))
        return vectors
