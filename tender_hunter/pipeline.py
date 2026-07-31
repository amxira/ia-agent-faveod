"""Per-tender pipeline: parse -> chunk -> embed -> index -> evaluate -> score."""

from __future__ import annotations

import logging
import os

from tender_hunter import config
from tender_hunter.embedding.base import Embedder
from tender_hunter.models import FaveodReport, Tender
from tender_hunter.parse.chunker import chunk_text
from tender_hunter.parse.documents import extract_pages
from tender_hunter.reasoning.engine import CriteriaEngine
from tender_hunter.reasoning.scoring import build_summary, compute_fit_score
from tender_hunter.vectorstore.store import VectorStore

log = logging.getLogger(__name__)

_MAX_DOWNLOAD_BYTES = 25 * 1024 * 1024


class TenderPipeline:
    def __init__(self, embedder: Embedder, store: VectorStore, engine: CriteriaEngine):
        self.embedder = embedder
        self.store = store
        self.engine = engine

    def run(self, tender: Tender) -> FaveodReport:
        documents_analyzed = 0

        for doc in tender.documents:
            path = self._materialize(doc.name, doc.local_path, doc.url, tender.id)
            if not path:
                continue
            pages = extract_pages(path)
            if not any(p.strip() for p in pages):
                continue
            chunks = chunk_text(pages, config.CHUNK_SIZE, config.CHUNK_OVERLAP)
            if not chunks:
                continue
            try:
                vectors = self.embedder.embed_texts([c.text for c in chunks])
                self.store.index_tender(tender.id, doc.name, chunks, vectors)
                documents_analyzed += 1
            except Exception as exc:  # noqa: BLE001
                log.warning("[%s] embedding/indexing failed for %s: %s", tender.id, doc.name, exc)

        criteria = self.engine.evaluate(tender.id)
        fit_score, grade, manual = compute_fit_score(criteria)
        summary = build_summary(criteria)

        if not criteria:
            log.warning("[%s] no criteria evaluated", tender.id)

        return FaveodReport(
            tender_id=tender.id,
            source=tender.source,
            title=tender.title,
            country=tender.country,
            region=tender.region,
            deadline=tender.deadline,
            url=tender.url,
            fit_score=fit_score,
            fit_grade=grade,
            requires_manual_review=manual,
            documents_analyzed=documents_analyzed,
            criteria=criteria,
            summary=summary,
        )

    @staticmethod
    def _materialize(name: str, local_path: str | None, url: str | None, tender_id: str) -> str | None:
        if local_path and os.path.exists(local_path):
            return local_path
        if url:
            return _download(url, name, tender_id)
        return None


def _download(url: str, name: str, tender_id: str) -> str | None:
    """Best-effort download of a remote tender document; None on any failure."""
    import requests

    from tender_hunter import config as cfg

    target_dir = os.path.join(cfg.DOWNLOAD_DIR, tender_id)
    os.makedirs(target_dir, exist_ok=True)
    safe = "".join(c if c.isalnum() or c in ".-_" else "_" for c in name) or "document"
    path = os.path.join(target_dir, safe)
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return path
    try:
        resp = requests.get(url, timeout=cfg.HTTP_TIMEOUT, headers={"User-Agent": cfg.USER_AGENT})
        resp.raise_for_status()
        if len(resp.content) > _MAX_DOWNLOAD_BYTES:
            log.warning("[%s] download too large: %s", tender_id, url)
            return None
        with open(path, "wb") as fh:
            fh.write(resp.content)
        return path
    except Exception as exc:  # noqa: BLE001
        log.warning("[%s] download failed for %s: %s", tender_id, url, exc)
        return None
