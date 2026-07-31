"""Google Gemini embeddings (free tier) via the REST API.

No extra SDK dependency: plain POST to the generativelanguage endpoint with the
API key as query parameter. Embedding vectors are L2-normalized and reduced to
config.VECTOR_SIZE dimensions so the whole system has one fixed vector size.
"""

from __future__ import annotations

import logging

import requests

from tender_hunter import config
from tender_hunter.embedding.base import Embedder, l2_normalize

log = logging.getLogger(__name__)

_BATCH = 90  # batchEmbedContents allows up to 100; stay under to be safe


class GeminiEmbedder(Embedder):
    def __init__(self, api_key: str = "", model: str = "", dimension: int = 768):
        self.api_key = api_key or config.GEMINI_API_KEY
        self.model = model or config.GEMINI_EMBED_MODEL
        self.dimension = dimension or config.VECTOR_SIZE
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is not set")

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for i in range(0, len(texts), _BATCH):
            batch = texts[i : i + _BATCH]
            payload = {
                "model": f"models/{self.model}",
                "requests": [
                    {
                        "model": f"models/{self.model}",
                        "content": {"parts": [{"text": text or " "}]},
                        "taskType": "RETRIEVAL_DOCUMENT",
                        "outputDimensionality": self.dimension,
                    }
                    for text in batch
                ],
            }
            url = f"{config.GEMINI_EMBED_URL}/models/{self.model}:batchEmbedContents"
            resp = requests.post(url, params={"key": self.api_key}, json=payload, timeout=config.HTTP_TIMEOUT)
            resp.raise_for_status()
            for emb in resp.json().get("embeddings", []):
                values = emb.get("values") or []
                if len(values) != self.dimension:
                    # Older/model-locked dimensions fall back to actual size.
                    self.dimension = len(values)
                vectors.append(l2_normalize(values))
        return vectors
