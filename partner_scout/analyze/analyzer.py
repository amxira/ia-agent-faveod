"""LLM company profiler with anti-hallucination guardrails (Task 3.2).

Every quote the model returns must match the fetched page text (verbatim after
normalization). Claims whose evidence fails the check are dropped and the field
is reported as unspecified / manual-review, exactly like Agent 1's guardrails.
"""

from __future__ import annotations

import logging
import re

from partner_scout import config
from partner_scout.analyze.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE, format_pages
from partner_scout.models import Citation, ESNCompany, ESNProfile, PageText
from tender_hunter.llm.client import LLMClient

log = logging.getLogger(__name__)

_VALID_TECH_FOCUS = {
    "custom_development",
    "mixed",
    "low_code_reseller",
    "proprietary_reseller",
    "unspecified",
}
_VALID_SCALE = {"startup", "smb", "enterprise", "public_sector", "mixed", "unspecified"}
_CORE_FIELDS = ("tech_focus", "services", "client_references")
_MIN_EVIDENCE_CHARS = 8


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().lower()


class ProfileAnalyzer:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def analyze(self, company: ESNCompany, pages: list[PageText]) -> ESNProfile:
        base = ESNProfile(
            company_id=company.id,
            company_name=company.name,
            website=company.website,
            pages_analyzed=len(pages),
        )

        if not pages:
            base.guardrail = "no_pages"
            base.fields_unspecified = list(_CORE_FIELDS)
            base.rationale = "No analyzable website pages were found. Manual review required."
            return base

        corpus_blob = " ".join(page.text for page in pages)
        if len(corpus_blob) < config.MIN_PAGE_TEXT_CHARS:
            base.guardrail = "content_too_thin"
            base.fields_unspecified = list(_CORE_FIELDS)
            base.rationale = "The website content is too thin to analyze safely. Manual review required."
            return base

        if not self.llm.available:
            base.guardrail = "llm_unavailable"
            base.fields_unspecified = list(_CORE_FIELDS)
            base.rationale = "No LLM configured; profile not evaluated. Manual review required."
            return base

        user_prompt = USER_PROMPT_TEMPLATE.format(
            website=company.website,
            n=len(pages),
            pages=format_pages(pages),
        )
        raw = self.llm.chat_json(SYSTEM_PROMPT, user_prompt)
        if raw is None:
            base.guardrail = "llm_unavailable"
            base.fields_unspecified = list(_CORE_FIELDS)
            base.rationale = "LLM could not produce a profile; manual review required."
            return base

        citations = _verify_all(raw, pages)
        verified_evidence = {c.snippet for c in citations}

        base.confidence = max(0.0, min(1.0, float(raw.get("confidence", 0.0) or 0.0)))
        base.rationale = str(raw.get("rationale", ""))[:2000]
        base.citations = citations
        base.evidence = sorted(verified_evidence)

        base.company_name = str(raw.get("company_name") or company.name)[:200]

        tech = str(raw.get("tech_focus", "")).strip().lower()
        base.tech_focus = tech if tech in _VALID_TECH_FOCUS else "unspecified"
        if base.tech_focus == "unspecified" or not _evidence_verified(raw.get("tech_focus_evidence"), verified_evidence):
            base.tech_focus = "unspecified"
            base.fields_unspecified.append("tech_focus")

        base.services = _verified_list(raw.get("services"), raw.get("services_evidence"), verified_evidence)
        base.client_references = _verified_list(raw.get("client_references"), raw.get("client_references_evidence"), verified_evidence)
        base.languages = _verified_languages(raw.get("languages"), raw.get("languages_evidence"), verified_evidence)
        base.contact_url = _verified_scalar(raw.get("contact_url"), raw.get("contact_url_evidence"), verified_evidence)
        base.employees_estimate = _verified_scalar(raw.get("employees_estimate"), raw.get("employees_estimate_evidence"), verified_evidence)

        scale = str(raw.get("project_scale", "")).strip().lower()
        base.project_scale = scale if scale in _VALID_SCALE else "unspecified"
        if base.project_scale == "unspecified" or not _evidence_verified(raw.get("project_scale_evidence"), verified_evidence):
            base.project_scale = "unspecified"
            base.fields_unspecified.append("project_scale")

        confirmed = raw.get("country_confirmed")
        base.country_confirmed = bool(confirmed) and _evidence_verified(raw.get("country_confirmed_evidence"), verified_evidence)

        for field in _CORE_FIELDS:
            value = getattr(base, field)
            if field in ("tech_focus",):
                empty = base.tech_focus == "unspecified"
            else:
                empty = not value
            if empty and field not in base.fields_unspecified:
                base.fields_unspecified.append(field)

        if not verified_evidence:
            base.guardrail = "evidence_not_found"
            base.rationale = (
                "The model's quotes could not be matched verbatim to the website pages; "
                "profile suppressed to prevent hallucination. Manual review required."
            )
            base.confidence = 0.0

        base.fields_unspecified = list(dict.fromkeys(base.fields_unspecified))
        return base


def _verify_all(raw: dict, pages: list[PageText]) -> list[Citation]:
    """Verify every evidence quote in the raw response against the page texts."""
    blob_norm = _normalize(" ".join(page.text for page in pages))
    candidates: list[str] = []

    def collect(key: str) -> None:
        value = raw.get(key)
        if isinstance(value, list):
            candidates.extend(str(v) for v in value if v)
        elif value:
            candidates.append(str(value))

    for key in raw:
        if key.endswith("_evidence"):
            collect(key)

    citations: list[Citation] = []
    seen: set[str] = set()
    for snippet in candidates:
        snippet = (snippet or "").strip()
        if len(snippet) < _MIN_EVIDENCE_CHARS:
            continue
        snorm = _normalize(snippet)
        if snorm in blob_norm or blob_norm in snorm:
            if snorm in seen:
                continue
            seen.add(snorm)
            best = max(pages, key=lambda p: _overlap(p.text, snippet))
            citations.append(Citation(document=best.url, kind=best.kind, snippet=snippet[:600]))
    return citations


def _evidence_verified(evidence, verified_evidence: set[str]) -> bool:
    if not evidence:
        return False
    for item in evidence:
        item = str(item).strip()
        if len(item) >= _MIN_EVIDENCE_CHARS and item[:600] in verified_evidence:
            return True
    return False


def _verified_list(values, evidence, verified_evidence: set[str]) -> list[str]:
    if not _evidence_verified(evidence, verified_evidence):
        return []
    return [str(v).strip()[:300] for v in (values or []) if str(v).strip()][:10]


def _verified_scalar(value, evidence, verified_evidence: set[str]) -> str:
    if not value or not _evidence_verified(evidence, verified_evidence):
        return ""
    return str(value).strip()[:500]


def _verified_languages(values, evidence, verified_evidence: set[str]) -> list[str]:
    if not _evidence_verified(evidence, verified_evidence):
        return []
    langs = []
    for value in (values or []):
        code = str(value).strip().lower()[:2]
        if code and code not in langs and code.isalpha():
            langs.append(code)
    return langs[:5]


def _overlap(doc_text: str, snippet: str) -> float:
    words = set(_normalize(snippet).split())
    if not words:
        return 0.0
    text = set(_normalize(doc_text).split())
    return len(words & text) / len(words)
