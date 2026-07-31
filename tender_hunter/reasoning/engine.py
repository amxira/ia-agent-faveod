"""Reasoning engine with strict anti-hallucination guardrails (Task 2.3).

Per criterion:
  1. Embed the criterion question and retrieve the top-k chunks from the store.
  2. If the max similarity to any chunk is below config.SIMILARITY_THRESHOLD
     (0.75), the criterion is NOT passed to the LLM and is reported as
     "Unspecified - Manual review required".
  3. Otherwise DeepSeek-R1 evaluates using only the retrieved excerpts.
  4. Every evidence quote the model returns is cross-checked against the
     retrieved text. Non-matching quotes are dropped; if no quote matches,
     the criterion is forced to manual review (evidence guardrail).
"""

from __future__ import annotations

import logging
import re

from tender_hunter import config
from tender_hunter.embedding.base import Embedder
from tender_hunter.llm.client import LLMClient
from tender_hunter.models import GUARDRAIL, CriterionResult, Citation
from tender_hunter.reasoning.prompts import CRITERIA, SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from tender_hunter.vectorstore.store import RetrievedChunk, VectorStore

log = logging.getLogger(__name__)

_VALID_STATUS = {"SATISFIED", "PARTIAL", "NOT_SATISFIED"}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().lower()


class CriteriaEngine:
    def __init__(
        self,
        llm: LLMClient,
        embedder: Embedder,
        store: VectorStore,
        threshold: float = 0.75,
        top_k: int = 6,
    ):
        self.llm = llm
        self.embedder = embedder
        self.store = store
        self.threshold = threshold or config.SIMILARITY_THRESHOLD
        self.top_k = top_k or config.TOP_K

    def evaluate(self, tender_id: str) -> list[CriterionResult]:
        results: list[CriterionResult] = []
        for criterion in CRITERIA:
            results.append(self._evaluate_one(tender_id, criterion["key"], criterion["label"], criterion["question"]))
        return results

    def _evaluate_one(self, tender_id: str, key: str, label: str, question: str) -> CriterionResult:
        query_vector = self.embedder.embed(question)
        hits = self.store.search(tender_id, query_vector, self.top_k)
        max_sim = max((h.score for h in hits), default=0.0)

        base = CriterionResult(
            criterion=key,
            label=label,
            status=GUARDRAIL,
            similarity_score=round(max_sim, 4),
        )

        if not hits or max_sim < self.threshold:
            base.guardrail = "similarity_below_threshold" if hits else "no_relevant_document"
            base.rationale = (
                f"Embedding similarity {max_sim:.3f} is below the {self.threshold:.2f} guardrail "
                "threshold; the criterion was NOT sent to the model. Manual review required."
            )
            return base

        excerpts = self._format_excerpts(hits)
        user_prompt = USER_PROMPT_TEMPLATE.format(
            criterion_label=label, criterion_question=question, excerpts=excerpts
        )
        raw = self.llm.chat_json(SYSTEM_PROMPT, user_prompt)
        if raw is None:
            base.guardrail = "llm_unavailable"
            base.rationale = "LLM could not produce a verdict; manual review required."
            return base

        status = str(raw.get("status", "")).strip().upper()
        confidence = float(raw.get("confidence", 0.0) or 0.0)
        evidence = [str(e) for e in (raw.get("evidence") or [])]

        citations, verified = self._verify_evidence(evidence, hits)
        if not verified:
            base.guardrail = "evidence_not_found"
            base.rationale = (
                "The model's quotes could not be matched verbatim to the retrieved excerpts; "
                "verdict suppressed to prevent hallucination. Manual review required."
            )
            base.confidence = 0.0
            return base

        base.status = status if status in _VALID_STATUS else GUARDRAIL
        base.guardrail = None if base.status in _VALID_STATUS else "invalid_status"
        base.confidence = max(0.0, min(1.0, confidence))
        base.rationale = str(raw.get("rationale", ""))[:2000]
        base.citations = citations
        return base

    @staticmethod
    def _format_excerpts(hits: list[RetrievedChunk]) -> str:
        lines = []
        for i, hit in enumerate(hits, start=1):
            lines.append(f"[EXCERPT {i} | doc={hit.document} | page={hit.page} | score={hit.score:.3f}]")
            lines.append(hit.text.strip())
        return "\n".join(lines)

    @staticmethod
    def _verify_evidence(evidence: list[str], hits: list[RetrievedChunk]) -> tuple[list[Citation], bool]:
        """Return (citations, any_verified). Drops hallucinated quotes."""
        citations: list[Citation] = []
        blob = " ".join(hit.text for hit in hits)
        blob_norm = _normalize(blob)
        for snippet in evidence:
            snippet = (snippet or "").strip()
            if len(snippet) < 10:
                continue
            snorm = _normalize(snippet)
            if snorm in blob_norm or blob_norm in snorm:
                # Attribute to the most similar hit (heuristic by word overlap).
                best = max(hits, key=lambda h: _overlap(h.text, snippet))
                citations.append(
                    Citation(
                        document=best.document,
                        page=best.page,
                        chunk_id=best.chunk_id,
                        snippet=snippet[:600],
                    )
                )
        return citations, bool(citations)


def _overlap(doc_text: str, snippet: str) -> float:
    words = set(_normalize(snippet).split())
    if not words:
        return 0.0
    text = set(_normalize(doc_text).split())
    return len(words & text) / len(words)
