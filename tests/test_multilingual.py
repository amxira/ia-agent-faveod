"""Task 5.2 - End-to-end multilingual validation (French / English / Arabic).

Run:  python tests/test_multilingual.py
Covers the exact Phase-5 asks:
  1. Agent 1 parses REAL French, English and Arabic sample tender documents.
  2. Anti-hallucination rules hold in every language: a model that returns
     fabricated quotes is suppressed to "Unspecified - Manual review required",
     and an unavailable LLM never guesses.
  3. Fit-score honesty: any criterion held in guardrail forces manual review.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tender_hunter import config
from tender_hunter.embedding.base import Embedder
from tender_hunter.ingest.sample_data import build_sample_tenders
from tender_hunter.llm.client import LLMClient
from tender_hunter.models import GUARDRAIL, CriterionResult
from tender_hunter.parse.chunker import chunk_text
from tender_hunter.parse.documents import extract_pages
from tender_hunter.reasoning.engine import CriteriaEngine
from tender_hunter.reasoning.scoring import compute_fit_score
from tender_hunter.vectorstore.store import VectorStore

HIGH_VEC = [1.0] + [0.0] * 767


class FlatEmbedder(Embedder):
    """Everything embeds to HIGH_VEC so retrieval always passes the gate."""

    dimension = 768

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [list(HIGH_VEC) for _ in texts]


class FakeLLM(LLMClient):
    def __init__(self, responses: list[dict | None]):
        self._responses = responses
        self.calls = 0

    @property
    def available(self) -> bool:
        return True

    def chat_json(self, system: str, user: str) -> dict | None:
        self.calls += 1
        return self._responses.pop(0) if self._responses else None


def _find_doc(language: str):
    for tender in build_sample_tenders():
        if tender["language"] == language:
            return tender
    raise AssertionError(f"no sample tender in language {language!r}")


def _parsed_corpus(language: str) -> tuple[str, str, str, str]:
    """Return (tender_id, doc_name, doc_path, full_text) for a real sample doc."""
    tender = _find_doc(language)
    doc = tender["documents"][0]
    path = doc["local_path"]
    assert os.path.exists(path), f"sample document missing: {path}"
    pages = extract_pages(path)
    text = "\n\n".join(p for p in pages if p.strip())
    return tender["id"], doc["name"], path, text


def _engine_for(text: str, doc_name: str, tender_id: str, llm: LLMClient) -> CriteriaEngine:
    chunks = chunk_text([text])
    vectors = FlatEmbedder().embed_texts([c.text for c in chunks])
    store = VectorStore(dimension=768)
    store.index_tender(tender_id, doc_name, chunks, vectors)
    return CriteriaEngine(llm, FlatEmbedder(), store, threshold=0.75, top_k=6)


def test_parse_french_pdf():
    _, name, _, text = _parsed_corpus("fr")
    assert len(text) >= 100, (name, len(text))
    assert any(w in text.lower() for w in ("administration", "code source", "propriété")), text[:200]
    print(f"ok test_parse_french_pdf ({name}, {len(text)} chars)")


def test_parse_english_pdf():
    _, name, _, text = _parsed_corpus("en")
    assert len(text) >= 100, (name, len(text))
    assert any(w in text.lower() for w in ("development", "software", "procurement")), text[:200]
    print(f"ok test_parse_english_pdf ({name}, {len(text)} chars)")


def test_parse_arabic_docx():
    _, name, _, text = _parsed_corpus("ar")
    assert len(text) >= 100, (name, len(text))
    assert any("\u0600" <= ch <= "\u06ff" for ch in text), "expected Arabic script"
    print(f"ok test_parse_arabic_docx ({name}, {len(text)} chars)")


def test_guardrails_multilingual_evidence():
    for language in ("fr", "en", "ar"):
        tender_id, doc_name, _, text = _parsed_corpus(language)
        hallucinated = {"status": "SATISFIED", "confidence": 0.95, "evidence": ["this quote does not exist in the document"]}
        llm = FakeLLM([hallucinated] * 4)
        engine = _engine_for(text, doc_name, tender_id, llm)
        results = engine.evaluate(tender_id)
        assert len(results) == 4
        for res in results:
            assert res.status == GUARDRAIL, (language, res.criterion, res.status)
            assert res.guardrail == "evidence_not_found", (language, res.guardrail)
            assert res.citations == []
        assert llm.calls >= 4
    print("ok test_guardrails_multilingual_evidence")


def test_guardrails_multilingual_llm_unavailable():
    for language in ("fr", "en", "ar"):
        tender_id, doc_name, _, text = _parsed_corpus(language)
        no_llm = LLMClient(api_key="")
        engine = _engine_for(text, doc_name, tender_id, no_llm)
        results = engine.evaluate(tender_id)
        assert all(r.guardrail == "llm_unavailable" for r in results), language
    print("ok test_guardrails_multilingual_llm_unavailable")


def test_multilingual_fit_score_honesty():
    for language in ("fr", "en", "ar"):
        tender_id, doc_name, _, text = _parsed_corpus(language)
        no_llm = LLMClient(api_key="")
        results = _engine_for(text, doc_name, tender_id, no_llm).evaluate(tender_id)
        score, grade, manual = compute_fit_score(results)
        assert manual is True, (language, grade)
        assert "(REVIEW)" in grade, (language, grade)
        assert score < 40, (language, score)
    print("ok test_multilingual_fit_score_honesty")


if __name__ == "__main__":
    test_parse_french_pdf()
    test_parse_english_pdf()
    test_parse_arabic_docx()
    test_guardrails_multilingual_evidence()
    test_guardrails_multilingual_llm_unavailable()
    test_multilingual_fit_score_honesty()
    print("\nALL MULTILINGUAL VALIDATION TESTS PASSED")
