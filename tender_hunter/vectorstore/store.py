"""Qdrant vector store with a transparent in-memory fallback (Task 2.2).

Connects to QDRANT_URL when set (e.g. the docker-compose Qdrant service);
otherwise uses Qdrant's in-memory mode so dev needs no server at all.
Collections use cosine distance, matching the L2-normalized embedder output.
"""

from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import dataclass

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
)

from tender_hunter import config
from tender_hunter.parse.chunker import Chunk

log = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    chunk_id: str
    document: str
    page: int
    text: str
    score: float


class VectorStore:
    def __init__(self, url: str = "", api_key: str = "", collection: str = "", dimension: int = 768):
        self.url = url or config.QDRANT_URL
        self.collection = collection or config.QDRANT_COLLECTION
        self.dimension = dimension
        # Guard concurrent index/search when the shared store is used from
        # parallel LangGraph branches (needed for the in-memory backend).
        self._lock = threading.RLock()

        if self.url:
            log.info("connecting to Qdrant at %s", self.url)
            self.client = QdrantClient(url=self.url, api_key=api_key or config.QDRANT_API_KEY or None)
            self.mode = "server"
        else:
            log.info("QDRANT_URL not set; using in-memory Qdrant (dev)")
            self.client = QdrantClient(":memory:")
            self.mode = "memory"

        self._ensure_collection()

    def _ensure_collection(self) -> None:
        existing = [c.name for c in self.client.get_collections().collections]
        if self.collection in existing:
            return
        self.client.create_collection(
            collection_name=self.collection,
            vectors_config=VectorParams(size=self.dimension, distance=Distance.COSINE),
        )
        log.info("created collection %r (dim=%d)", self.collection, self.dimension)

    def reset(self) -> None:
        self.client.recreate_collection(
            collection_name=self.collection,
            vectors_config=VectorParams(size=self.dimension, distance=Distance.COSINE),
        )

    def index_tender(self, tender_id: str, doc_name: str, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("chunks/vectors length mismatch")
        points = []
        for idx, (chunk, vec) in enumerate(zip(chunks, vectors)):
            points.append(
                PointStruct(
                    id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{tender_id}/{doc_name}/{idx}")),
                    vector=vec,
                    payload={
                        "tender_id": tender_id,
                        "document": doc_name,
                        "page": chunk.page,
                        "text": chunk.text,
                        "chunk_index": idx,
                    },
                )
            )
        if points:
            with self._lock:
                self.client.upsert(collection_name=self.collection, points=points)

    def search(self, tender_id: str, query_vector: list[float], top_k: int = 6) -> list[RetrievedChunk]:
        with self._lock:
            resp = self.client.query_points(
                collection_name=self.collection,
                query=query_vector,
                limit=top_k,
                with_payload=True,
            )
            results: list[RetrievedChunk] = []
            for hit in resp.points:
                payload = hit.payload or {}
                if payload.get("tender_id") != tender_id:
                    continue
                results.append(
                    RetrievedChunk(
                        chunk_id=str(hit.id),
                        document=str(payload.get("document", "")),
                        page=int(payload.get("page", 0)),
                        text=str(payload.get("text", "")),
                        score=float(hit.score),
                    )
                )
            return results

    def delete_tender(self, tender_id: str) -> None:
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        try:
            self.client.delete(
                collection_name=self.collection,
                points_selector=Filter(
                    must=[FieldCondition(key="tender_id", match=MatchValue(value=tender_id))]
                ),
            )
        except Exception:  # noqa: BLE001 - best effort cleanup
            pass
