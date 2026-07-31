"""Guardrail & scoring tests for the reasoning engine (plain pytest-free asserts).

Run:  python tests/test_guardrails.py
Covers: similarity gate, LLM verdict + verbatim citation, hallucinated quotes,
invalid status, unavailable LLM, and the Faveod Fit Score formula.
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tender_hunter.embedding.base import Embedder
from tender_hunter.llm.client import LLMClient
from tender_hunter.models import GUARDRAIL, CriterionResult
from tender_hunter.reasoning.engine import CriteriaEngine
from tender_hunter.reasoning.scoring import WEIGHTS, compute_fit_score
from tender_hunter.vectorstore.store import VectorStore

HIGH_VEC = [1.0] + [0.0] * 767
LOW_DOC = [1.0] + [0.0] * 767          # docs in the gate test
LOW_QUERY = [0.0, 1.0] + [0.0] * 766   # queries in the gate test (cosine 0 vs LOW_DOC)


class MapEmbedder(Embedder):
    """Vectors per exact text; queries not in the map fall back to `default`."""

    dimension = 768

    def __init__(self, mapping: dict[str, list[float]], default: list[float]):
        self.mapping = mapping
        self.default = default

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self.mapping.get(t, self.default) for t in texts]


class FakeLLM(LLMClient):
    def __init__(self, responses: list[dict | None]):
        self._responses = responses
        self.calls = 0

    @property
    def available(self) -> bool:
        return True

    def chat_json(self, system: str, user: str) -> dict | None:
        self.calls += 1
        return self._responses.pop(0)


def _store(texts: list[str], embedder: Embedder) -> VectorStore:
    store = VectorStore(dimension=embedder.dimension)
    chunks = [__import__("tender_hunter.parse.chunker", fromlist=["Chunk"]).Chunk(text=t, page=i + 1) for i, t in enumerate(texts)]
    vecs = embedder.embed_texts([c.text for c in chunks])
    store.index_tender("T1", "doc.pdf", chunks, vecs)
    return store


def _status_of(criteria: list[CriterionResult], key: str) -> CriterionResult:
    return next(c for c in criteria if c.criterion == key)


def test_similarity_gate():
    doc = "nothing relevant here"
    store = _store([doc], MapEmbedder({doc: LOW_DOC}, LOW_QUERY))
    llm = FakeLLM([{"status": "SATISFIED", "evidence": ["x"]}])
    engine = CriteriaEngine(llm, MapEmbedder({doc: LOW_DOC}, LOW_QUERY), store, threshold=0.75, top_k=4)
    crit = engine.evaluate("T1")
    res = _status_of(crit, "ip_ownership")
    assert res.status == GUARDRAIL, res
    assert res.guardrail == "similarity_below_threshold"
    assert llm.calls == 0, "LLM must not be called below threshold"
    print("ok test_similarity_gate")


def test_llm_verdict_with_citations():
    doc = "ownership passes to the client and all rights are transferred completely"
    store = _store([doc], MapEmbedder({doc: HIGH_VEC}, HIGH_VEC))
    verdict = {"status": "SATISFIED", "confidence": 0.92, "rationale": "Full transfer.", "evidence": ["ownership passes to the client and all rights"]}
    llm = FakeLLM([verdict, verdict, verdict, verdict])
    engine = CriteriaEngine(llm, MapEmbedder({doc: HIGH_VEC}, HIGH_VEC), store, threshold=0.75, top_k=4)
    crit = engine.evaluate("T1")
    res = _status_of(crit, "ip_ownership")
    assert res.status == "SATISFIED", res
    assert res.similarity_score == 1.0
    assert len(res.citations) == 1
    assert res.citations[0].document == "doc.pdf"
    assert "ownership passes to the client" in res.citations[0].snippet
    print("ok test_llm_verdict_with_citations")


def test_hallucinated_evidence():
    doc = "the platform will be hosted in a local datacentre"
    store = _store([doc], MapEmbedder({doc: HIGH_VEC}, HIGH_VEC))
    bad = {"status": "SATISFIED", "evidence": ["this quote does not exist anywhere"]}
    llm = FakeLLM([bad, bad, bad, bad])
    engine = CriteriaEngine(llm, MapEmbedder({doc: HIGH_VEC}, HIGH_VEC), store, threshold=0.75, top_k=4)
    crit = engine.evaluate("T1")
    res = _status_of(crit, "security_quality")
    assert res.status == GUARDRAIL, res
    assert res.guardrail == "evidence_not_found"
    print("ok test_hallucinated_evidence")


def test_invalid_status():
    doc = "the client owns the code outright"
    store = _store([doc], MapEmbedder({doc: HIGH_VEC}, HIGH_VEC))
    bad = {"status": "maybe", "evidence": ["the client owns the code"]}
    llm = FakeLLM([bad, bad, bad, bad])
    engine = CriteriaEngine(llm, MapEmbedder({doc: HIGH_VEC}, HIGH_VEC), store, threshold=0.75, top_k=4)
    crit = engine.evaluate("T1")
    res = _status_of(crit, "ip_ownership")
    assert res.status == GUARDRAIL, res
    assert res.guardrail == "invalid_status"
    print("ok test_invalid_status")


def test_llm_unavailable():
    doc = "the client owns the code outright"
    store = _store([doc], MapEmbedder({doc: HIGH_VEC}, HIGH_VEC))
    no_llm = LLMClient(api_key="")  # explicitly no key -> available False
    engine = CriteriaEngine(no_llm, MapEmbedder({doc: HIGH_VEC}, HIGH_VEC), store, threshold=0.75, top_k=4)
    crit = engine.evaluate("T1")
    res = _status_of(crit, "ip_ownership")
    assert res.status == GUARDRAIL, res
    assert res.guardrail == "llm_unavailable"
    print("ok test_llm_unavailable")


def test_fit_score():
    def c(k, s):
        return CriterionResult(criterion=k, label=k, status=s, similarity_score=0.9)

    all_strong = [c(k, "SATISFIED") for k in WEIGHTS]
    score, grade, manual = compute_fit_score(all_strong)
    assert score == 100.0 and "STRONG FIT" in grade and not manual, (score, grade)

    mixed = [
        c("ip_ownership", "SATISFIED"),
        c("security_quality", "PARTIAL"),
        c("timeline", "NOT_SATISFIED"),
        c("green_it", "SATISFIED"),
    ]
    score, grade, manual = compute_fit_score(mixed)
    expected = (WEIGHTS["ip_ownership"] * 1.0 + WEIGHTS["security_quality"] * 0.5 + WEIGHTS["green_it"] * 1.0) / sum(WEIGHTS.values()) * 100
    assert abs(score - round(expected, 1)) < 0.01, (score, expected)

    manual_req = all_strong + [c("green_it", GUARDRAIL)]
    score, grade, manual = compute_fit_score(manual_req)
    assert manual and "(REVIEW)" in grade
    print("ok test_fit_score")


if __name__ == "__main__":
    test_similarity_gate()
    test_llm_verdict_with_citations()
    test_hallucinated_evidence()
    test_invalid_status()
    test_llm_unavailable()
    test_fit_score()
    print("\nALL GUARDRAIL TESTS PASSED")
