"""Google Gemini embeddings (free tier) via the REST API.

No extra SDK dependency: plain POST to the generativelanguage endpoint with the
API key as query parameter. Embedding vectors are L2-normalized and reduced to
config.VECTOR_SIZE dimensions so the whole system has one fixed vector size.

Free-tier rate limits are handled with a global throttle between batches and
exponential backoff with jitter on 429 / 5xx responses.
"""

from __future__ import annotations

import logging
import random
import threading
import time

import requests

from tender_hunter import config
from tender_hunter.embedding.base import Embedder, l2_normalize

log = logging.getLogger(__name__)

_BATCH = 90  # batchEmbedContents allows up to 100; stay under to be safe
_MAX_ATTEMPTS = 3

_last_call: list[float] = [0.0]
_throttle_lock = threading.Lock()


def _throttle() -> None:
    """Enforce a minimum interval between embed batches (shared across threads)."""
    with _throttle_lock:
        now = time.monotonic()
        wait = config.GEMINI_RATE_LIMIT_SLEEP - (now - _last_call[0])
        if wait > 0:
            time.sleep(wait)
        _last_call[0] = time.monotonic()


class GeminiEmbedder(Embedder):
    def __init__(self, api_key: str = "", model: str = "", dimension: int = 768):
        self.api_key = api_key or config.GEMINI_API_KEY
        self.model = model or config.GEMINI_EMBED_MODEL
        self.dimension = dimension or config.VECTOR_SIZE
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is not set")
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": config.USER_AGENT})

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for i in range(0, len(texts), _BATCH):
            batch = texts[i : i + _BATCH]
            vectors.extend(self._embed_batch(batch))
        return vectors

    def _embed_batch(self, batch: list[str]) -> list[list[float]]:
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

        last_exc: Exception | None = None
        for attempt in range(_MAX_ATTEMPTS):
            try:
                _throttle()
                resp = self._session.post(url, params={"key": self.api_key}, json=payload, timeout=config.HTTP_TIMEOUT)
                if resp.status_code in (429, 500, 502, 503, 504):
                    raise _RetryableError(f"HTTP {resp.status_code}")
                resp.raise_for_status()
                out: list[list[float]] = []
                for emb in resp.json().get("embeddings", []):
                    values = emb.get("values") or []
                    if len(values) != self.dimension:
                        self.dimension = len(values)
                    out.append(l2_normalize(values))
                return out
            except _RetryableError as exc:
                last_exc = exc
                backoff = 2**attempt + random.uniform(0, 1)
                log.warning("Gemini embedding throttled (%s); retry %d in %.1fs", exc, attempt + 1, backoff)
                time.sleep(backoff)
            except requests.RequestException as exc:
                last_exc = exc
                if attempt == _MAX_ATTEMPTS - 1:
                    break
                time.sleep(2**attempt + random.uniform(0, 1))

        raise RuntimeError(f"Gemini embedding failed after {_MAX_ATTEMPTS} attempts: {last_exc}") from last_exc


class _RetryableError(Exception):
    pass
