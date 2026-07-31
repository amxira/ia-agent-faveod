"""Embedding factory: Gemini when possible, local hashing otherwise."""

from __future__ import annotations

import logging

from tender_hunter import config
from tender_hunter.embedding.base import Embedder
from tender_hunter.embedding.gemini import GeminiEmbedder
from tender_hunter.embedding.local import LocalEmbedder

log = logging.getLogger(__name__)


def get_embedder() -> Embedder:
    if config.EMBEDDING_PROVIDER == "gemini" and config.GEMINI_API_KEY:
        try:
            return GeminiEmbedder()
        except Exception as exc:  # noqa: BLE001
            log.warning("Gemini embedder unavailable (%s); falling back to local", exc)
    elif config.EMBEDDING_PROVIDER == "gemini":
        log.info("GEMINI_API_KEY not set; using local hashing embedder (offline mode)")
    return LocalEmbedder(config.VECTOR_SIZE)
