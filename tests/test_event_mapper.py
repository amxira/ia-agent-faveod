"""NER, classification, scoring & guardrail tests for the Event Mapper (pytest-free).

Run:  python tests/test_event_mapper.py
Covers: deterministic role classification, evidence guardrail in speaker
extraction, content-too-thin / LLM-unavailable honesty, score & priority
weights, an end-to-end offline pipeline run, and the LangGraph fan-out run.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from event_mapper.graph import build_components, build_graph, run_once
from event_mapper.ingest.sample_data import build_sample_events
from event_mapper.leads.classify import classify_role
from event_mapper.leads.score import compute_lead_score
from event_mapper.models import ITEvent, PageText, PersonRef
from event_mapper.ner.extractor import SpeakerExtractor
from event_mapper.pipeline import EventPipeline
from tender_hunter.llm.client import LLMClient


class FakeLLM(LLMClient):
    """Scripted or content-adaptive fake; mirrors the partner-scout test stub."""

    def __init__(self, responses: list | None = None):
        self._responses = responses or []
        self.calls = 0

    @property
    def available(self) -> bool:
        return True

    def chat_json(self, system: str, user: str) -> dict | None:
        self.calls += 1
        if self._responses:
            return self._responses.pop(0)
        return self._adaptive(system, user)

    def _adaptive(self, system: str, user: str) -> dict | None:
        if "LEAD CHALLENGES" in system:
            return {"challenges": "", "topics": [], "summary_evidence": [], "confidence": 0.0}
        prompt = user.upper()
        if "DIGITAL TRANSFORMATION AFRICA" in prompt:
            return {
                "persons": [
                    {"name": "Aminata Diallo", "job_title": "Chief Information Officer",
                     "company": "Ministry of Digital Economy of Senegal",
                     "role_evidence": ["Aminata Diallo, Chief Information Officer, Ministry of Digital Economy of Senegal."],
                     "title_evidence": ["Aminata Diallo, Chief Information Officer, Ministry of Digital Economy of Senegal."]},
                ],
                "event_summary": "E-government and sovereign cloud summit.",
            }
        if "CYBERSECURITY CONFERENCE DUBAI" in prompt:
            return {
                "persons": [
                    {"name": "Omar Al Farsi", "job_title": "Chief Information Security Officer",
                     "company": "Emirates NBD",
                     "role_evidence": ["Omar Al Farsi, Chief Information Security Officer, Emirates NBD."],
                     "title_evidence": ["Omar Al Farsi, Chief Information Security Officer, Emirates NBD."]},
                ],
                "event_summary": "Zero trust and cloud security in the GCC.",
            }
        if "CIO SUMMIT MIDDLE EAST" in prompt:
            return {
                "persons": [
                    {"name": "Fahad Al-Otaibi", "job_title": "Chief Technology Officer",
                     "company": "Saudi Digital Government Authority",
                     "role_evidence": ["Fahad Al-Otaibi, Chief Technology Officer, Saudi Digital Government Authority."],
                     "title_evidence": ["Fahad Al-Otaibi, Chief Technology Officer, Saudi Digital Government Authority."]},
                ],
                "event_summary": "AI in government and digital sovereignty.",
            }
        return {"persons": [], "event_summary": ""}


def _event_001() -> ITEvent:
    return next(e for e in build_sample_events() if e.id == "EV-2026-001")


def test_classify_roles():
    assert classify_role("Chief Information Officer") == (True, "c_level", "C-level technology executive (Chief Information Officer)")
    assert classify_role("Chief Information Security Officer") == (True, "c_level", "C-level technology executive (Chief Information Security Officer)")
    assert classify_role("Minister of Digital Economy") == (True, "government", "Government executive (minister/secretariat)")
    assert classify_role("IT Director") == (True, "director", "IT Director / Head of Technology")
    dm, seniority, _ = classify_role("IT Security Manager")
    assert dm is False and seniority == "manager"
    dm, seniority, _ = classify_role("Network Engineer")
    assert dm is False and seniority == "engineer"
    assert classify_role("")[1] == "unknown"
    print("ok test_classify_roles")


def test_extractor_evidence_guardrail():
    event = _event_001()
    bad = {
        "persons": [
            {"name": "Aminata Diallo", "job_title": "Chief Information Officer",
             "company": "Ministry of Digital Economy of Senegal",
             "role_evidence": ["this quote does not exist anywhere on the site"],
             "title_evidence": ["this quote does not exist anywhere on the site"]},
            {"name": "Ghost Speaker", "job_title": "CIO",
             "company": "Unknown",
             "role_evidence": ["Aminata Diallo, Chief Information Officer, Ministry of Digital Economy of Senegal."],
             "title_evidence": ["Aminata Diallo, Chief Information Officer, Ministry of Digital Economy of Senegal."]},
        ],
        "event_summary": "hallucinated",
    }
    extractor = SpeakerExtractor(FakeLLM([bad]))
    persons = extractor.extract(event, event.pages)
    assert persons, "no persons extracted at all"
    by_name = {p.name: p for p in persons}
    assert "Ghost Speaker" not in by_name, "unverifiable name must be dropped"
    aminata = by_name["Aminata Diallo"]
    assert aminata.verified is False, "non-verbatim evidence must not verify"
    assert aminata.guardrail == "evidence_not_found"
    assert aminata.title_evidence == []
    print("ok test_extractor_evidence_guardrail")


def test_extractor_llm_unavailable():
    event = _event_001()
    extractor = SpeakerExtractor(LLMClient(api_key=""))
    assert extractor.extract(event, event.pages) == []
    print("ok test_extractor_llm_unavailable")


def test_extractor_content_too_thin():
    event = _event_001()
    thin = [PageText(url=event.url, title="t", kind="home", text="A tiny page with almost no content to analyze.")]
    extractor = SpeakerExtractor(FakeLLM())
    assert extractor.extract(event, thin) == []
    print("ok test_extractor_content_too_thin")


def test_score_priority_weights():
    gov = PersonRef(name="A", job_title="CIO", company="Ministry", verified=True)
    event = _event_001()
    score, priority, manual = compute_lead_score(True, "government", event, gov, "legacy systems", ["cloud"])
    assert score >= 70 and priority == "HIGH PRIORITY" and not manual, (score, priority)

    eng = PersonRef(name="B", job_title="Network Engineer", company="Telco", verified=True)
    score, priority, _ = compute_lead_score(False, "engineer", event, eng, "", [])
    assert score < 50 and priority == "LOW PRIORITY", (score, priority)

    unverified = PersonRef(name="C", job_title="", company="", verified=False)
    score, _, manual = compute_lead_score(False, "unknown", event, unverified, "", [])
    assert manual is True and score < 40, (score, manual)
    print("ok test_score_priority_weights")


def test_pipeline_offline():
    event = _event_001()
    ner = {
        "persons": [
            {"name": "Aminata Diallo", "job_title": "Chief Information Officer",
             "company": "Ministry of Digital Economy of Senegal",
             "role_evidence": ["Aminata Diallo, Chief Information Officer, Ministry of Digital Economy of Senegal."],
             "title_evidence": ["Aminata Diallo, Chief Information Officer, Ministry of Digital Economy of Senegal."]},
            {"name": "Jean-Paul Kouassi", "job_title": "Software Engineer",
             "company": "Ivory Coast startup",
             "role_evidence": ["Jean-Paul Kouassi, Software Engineer, Ivory Coast startup."],
             "title_evidence": ["Jean-Paul Kouassi, Software Engineer, Ivory Coast startup."]},
        ],
        "event_summary": "Regional e-government and cloud summit.",
    }
    enrich_aminata = {
        "challenges": "Sovereign cloud and local hosting for e-government platforms.",
        "topics": ["Sovereign cloud and local hosting"],
        "summary_evidence": ["Session: Sovereign cloud and local hosting for e-government platforms."],
        "confidence": 0.9,
    }
    enrich_jean = {
        "challenges": "Building resilient micro-services in the cloud.",
        "topics": ["Micro-services"],
        "summary_evidence": ["Session: Building resilient micro-services in the cloud."],
        "confidence": 0.8,
    }
    llm = FakeLLM([ner, enrich_aminata, enrich_jean])
    pipeline = EventPipeline(SpeakerExtractor(llm), llm, proxy=None)
    cards = pipeline.run(event)

    assert len(cards) == 2, cards
    aminata = next(c for c in cards if c.person_name == "Aminata Diallo")
    assert aminata.decision_maker is True
    assert aminata.seniority == "c_level"
    assert aminata.priority == "HIGH PRIORITY"
    assert aminata.lead_score == 90.0, aminata.lead_score
    assert aminata.requires_manual_review is False
    assert aminata.pages_analyzed == 2
    assert "Sovereign cloud" in aminata.key_challenges

    jean = next(c for c in cards if c.person_name == "Jean-Paul Kouassi")
    assert jean.decision_maker is False
    assert jean.priority == "LOW PRIORITY"
    print("ok test_pipeline_offline")


def test_graph_fanout_offline():
    components = build_components(source="sample", llm=FakeLLM())
    graph = build_graph(components)
    state = run_once(components)
    leads = state.get("leads", [])
    assert isinstance(graph, object)
    assert len(leads) >= 3, f"expected fan-out leads, got {len(leads)}"
    top = [l for l in leads if l.priority == "HIGH PRIORITY"]
    decision = [l for l in leads if l.decision_maker]
    assert top and decision, (len(top), len(decision))
    print(f"ok test_graph_fanout_offline ({len(leads)} leads, {len(top)} high priority)")


if __name__ == "__main__":
    test_classify_roles()
    test_extractor_evidence_guardrail()
    test_extractor_llm_unavailable()
    test_extractor_content_too_thin()
    test_score_priority_weights()
    test_pipeline_offline()
    test_graph_fanout_offline()
    print("\nALL EVENT MAPPER TESTS PASSED")
