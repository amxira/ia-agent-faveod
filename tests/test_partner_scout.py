"""Qualification, affinity & guardrail tests for the Partner Scout (pytest-free).

Run:  python tests/test_partner_scout.py
Covers: qualification rules (custom dev vs resellers), affinity score weights,
no-pages/manual-review honesty, evidence guardrail, LLM-unavailable fallback,
and an end-to-end offline pipeline run with a deterministic fake LLM.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from partner_scout.analyze.analyzer import ProfileAnalyzer
from partner_scout.models import ESNCompany, ESNProfile, PageText
from partner_scout.pipeline import PartnerPipeline
from partner_scout.qualify.engine import compute_affinity, qualify
from partner_scout.search.sample_data import build_sample_companies
from tender_hunter.llm.client import LLMClient


def _profile(**overrides) -> ESNProfile:
    defaults = dict(
        company_id="X1",
        company_name="Custom Co",
        website="https://custom.example",
        tech_focus="custom_development",
        services=["Custom platforms"],
        client_references=[
            "Ministry of Interior", "National Bank", "City Hall",
            "Port Authority", "Energy Co",
        ],
        project_scale="public_sector",
        employees_estimate="120",
        languages=["fr", "en"],
        contact_url="info@custom.example",
        country_confirmed=True,
        confidence=0.95,
    )
    defaults.update(overrides)
    return ESNProfile(**defaults)


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


def test_qualify_custom_dev():
    profile = _profile()
    company = ESNCompany(id="X1", name="Custom Co", country="Morocco", website="https://custom.example")
    score, grade, manual = compute_affinity(profile, company.country, pages_analyzed=2)
    assert score == 100.0, score
    assert not manual, "fully verified profile must not require manual review"
    partner = qualify(company, profile, 2)
    assert partner.qualified is True, partner
    assert "STRONG PARTNER FIT" in grade
    assert partner.disqualification_reason == ""
    print("ok test_qualify_custom_dev")


def test_disqualify_resellers():
    for focus in ("low_code_reseller", "proprietary_reseller"):
        # Give the reseller the best possible references: score stays high, yet
        # the explicit competitor rule must exclude it from qualification.
        profile = _profile(tech_focus=focus, client_references=["Gov A", "Gov B", "Bank C", "Corp D", "Corp E"])
        company = ESNCompany(id="R1", name="Reseller", country="Morocco", website="https://reseller.example")
        partner = qualify(company, profile, 2)
        assert partner.qualified is False, (focus, partner)
        assert partner.disqualification_reason, focus
    print("ok test_disqualify_resellers")


def test_mixed_reduced():
    profile = _profile(tech_focus="mixed")
    company = ESNCompany(id="M1", name="Mixed Co", country="Egypt", website="https://mixed.example")
    score, _, _ = compute_affinity(profile, company.country, pages_analyzed=2)
    full = _profile()
    full_score, _, _ = compute_affinity(full, company.country, pages_analyzed=2)
    assert score < full_score, (score, full_score)
    partner = qualify(company, profile, 2)
    assert partner.qualified is True
    print("ok test_mixed_reduced")


def test_no_pages_manual():
    profile = _profile(
        tech_focus="unspecified",
        client_references=[],
        services=[],
        languages=[],
        contact_url="",
        country_confirmed=False,
        guardrail="no_pages",
        fields_unspecified=["tech_focus", "services", "client_references"],
        confidence=0.0,
    )
    company = ESNCompany(id="N1", name="No Site", country="Saudi Arabia", website="")
    score, grade, manual = compute_affinity(profile, company.country, pages_analyzed=0)
    partner = qualify(company, profile, 0)
    assert partner.qualified is False
    assert partner.requires_manual_review is True
    assert score < 40, score
    assert "REVIEW" in grade
    print("ok test_no_pages_manual")


def test_affinity_weights():
    company = ESNCompany(id="W1", name="W", country="Morocco", website="https://w.example")
    base = _profile()
    full, _, _ = compute_affinity(base, company.country, 2)
    assert full == 100.0

    no_refs = _profile(client_references=[])
    s, _, _ = compute_affinity(no_refs, company.country, 2)
    assert abs(s - 80.0) < 0.01, s  # references weight = 20%

    no_pages = _profile(contact_url="", languages=[], client_references=[])
    s, _, _ = compute_affinity(no_pages, company.country, 0)
    assert abs(s - 55.0) < 0.01, s  # 30 (custom) + 25 (country) = 55
    print("ok test_affinity_weights")


def test_analyzer_evidence_guardrail():
    page = PageText(url="https://co.example/", title="Co", kind="home",
                    text="The company builds bespoke custom software for banks in Cairo. "
                         "Established in 2015, we employ 80 engineers and deliver digital "
                         "banking platforms, government portals and payment gateways. "
                         "Our clients include the National Bank of Egypt and the Ministry "
                         "of Communications. We work in English and Arabic.")
    pages = [page]
    bad = {
        "company_name": "Fake Co",
        "tech_focus": "custom_development",
        "tech_focus_evidence": ["this quote does not exist anywhere on the site"],
        "services": ["Bespoke development"],
        "services_evidence": ["this quote does not exist anywhere on the site"],
        "client_references": ["National Bank of Egypt"],
        "client_references_evidence": ["this quote does not exist anywhere on the site"],
        "project_scale": "enterprise",
        "project_scale_evidence": ["this quote does not exist anywhere on the site"],
        "languages": ["en"],
        "languages_evidence": ["this quote does not exist anywhere on the site"],
        "contact_url": "",
        "contact_url_evidence": [],
        "country_confirmed": True,
        "country_confirmed_evidence": ["this quote does not exist anywhere on the site"],
        "rationale": "hallucinated",
        "confidence": 0.9,
    }
    company = ESNCompany(id="G1", name="Co", country="Egypt", website="https://co.example")
    analyzer = ProfileAnalyzer(FakeLLM([bad]))
    profile = analyzer.analyze(company, pages)
    assert profile.guardrail == "evidence_not_found", profile
    assert profile.tech_focus == "unspecified"
    assert profile.client_references == []
    assert profile.citations == []
    assert profile.confidence == 0.0
    assert {"tech_focus", "client_references"} <= set(profile.fields_unspecified)
    print("ok test_analyzer_evidence_guardrail")


def test_analyzer_llm_unavailable():
    page = PageText(url="https://co.example/", title="Co", kind="home",
                    text="The company builds bespoke custom software for banks in Cairo. "
                         "Established in 2015, we employ 80 engineers and deliver digital "
                         "banking platforms, government portals and payment gateways. "
                         "Our clients include the National Bank of Egypt and the Ministry "
                         "of Communications. We work in English and Arabic.")
    company = ESNCompany(id="U1", name="Co", country="Egypt", website="https://co.example")
    analyzer = ProfileAnalyzer(LLMClient(api_key=""))  # explicitly no key
    profile = analyzer.analyze(company, [page])
    assert profile.guardrail == "llm_unavailable"
    assert profile.fields_unspecified
    print("ok test_analyzer_llm_unavailable")


def test_sample_pipeline_offline():
    companies = build_sample_companies()
    atlas = next(c for c in companies if c.id == "PS-MA-001")
    verdict = {
        "company_name": "Atlas Custom Software",
        "tech_focus": "custom_development",
        "tech_focus_evidence": [
            "Nous développons des plateformes logicielles sur mesure pour les administrations publiques"
        ],
        "services": ["Développement sur mesure", "Intégration API"],
        "services_evidence": [
            "Nous maîtrisons Java, PHP, Python, React et l'intégration API"
        ],
        "client_references": ["Ministère de l'Intérieur", "Banque Centrale du Maroc"],
        "client_references_evidence": ["Ministère de l'Intérieur, Banque Centrale du Maroc"],
        "project_scale": "public_sector",
        "project_scale_evidence": ["Contrats publics signés avec l'État marocain depuis 2012"],
        "employees_estimate": "120 ingénieurs",
        "employees_estimate_evidence": ["Notre équipe de 120 ingénieurs conçoit des solutions souveraines hébergées au Maroc"],
        "languages": ["fr", "en"],
        "languages_evidence": ["Site disponible en français et en anglais"],
        "contact_url": "contact@atlascustom.example",
        "contact_url_evidence": ["Contactez-nous au contact@atlascustom.example"],
        "country_confirmed": True,
        "country_confirmed_evidence": ["agence de développement logiciel basée à Casablanca, Maroc"],
        "rationale": "Custom software agency with strong public-sector references.",
        "confidence": 0.95,
    }
    analyzer = ProfileAnalyzer(FakeLLM([verdict]))
    pipeline = PartnerPipeline(analyzer, proxy=None)
    partner = pipeline.run(atlas)
    assert partner.qualified is True, partner
    assert partner.affinity_score == 100.0, partner.affinity_score
    assert partner.pages_analyzed == 2
    assert "Ministère de l'Intérieur" in partner.client_references
    assert partner.requires_manual_review is False
    print("ok test_sample_pipeline_offline")


if __name__ == "__main__":
    test_qualify_custom_dev()
    test_disqualify_resellers()
    test_mixed_reduced()
    test_no_pages_manual()
    test_affinity_weights()
    test_analyzer_evidence_guardrail()
    test_analyzer_llm_unavailable()
    test_sample_pipeline_offline()
    print("\nALL PARTNER SCOUT TESTS PASSED")
