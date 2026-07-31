"""Partner qualification & Faveod Affinity Score (Task 3.3).

Deterministic rules on the guardrail-verified profile:
- Direct competitors (companies that ONLY resell proprietary / low-code
  products, with no custom development) are excluded regardless of score.
- Custom software capability, confirmed local presence, named client
  references / scale, analyzable web presence and language coverage drive the
  Faveod Affinity Score (0-100%).
- If a core field could not be verified (guardrail), the partner is flagged for
  manual review rather than guessed.
"""

from __future__ import annotations

from partner_scout import config
from partner_scout.models import ESNCompany, ESNProfile, QualifiedPartner

_CUSTOM_VALUE = {
    "custom_development": 1.0,
    "mixed": 0.6,
    "low_code_reseller": 0.0,
    "proprietary_reseller": 0.0,
    "unspecified": 0.0,
}
_WEIGHTS = {
    "custom": 0.30,
    "country": 0.25,
    "references": 0.20,
    "presence": 0.15,
    "languages": 0.10,
}
_MARKET_LANGS = {"fr", "en", "ar"}


def compute_affinity(profile: ESNProfile, country: str, pages_analyzed: int) -> tuple[float, str, bool]:
    custom = _CUSTOM_VALUE.get(profile.tech_focus, 0.0)
    country_score = 1.0 if country in config.TARGET_COUNTRIES else (0.0 if not country else 0.5)

    refs = profile.client_references
    if refs:
        ref_score = min(1.0, 0.5 + 0.1 * len(refs))
        if profile.project_scale in ("public_sector", "enterprise", "mixed"):
            ref_score = min(1.0, ref_score + 0.3)
    else:
        ref_score = 0.0

    presence = 0.0
    if pages_analyzed > 0:
        presence = 0.5
        if profile.contact_url:
            presence += 0.3
        if profile.website:
            presence += 0.2
        presence = min(presence, 1.0)

    overlap = len(set(profile.languages) & _MARKET_LANGS)
    lang_score = 1.0 if overlap >= 2 else (0.6 if overlap == 1 else (0.3 if profile.languages else 0.0))

    weighted = (
        _WEIGHTS["custom"] * custom
        + _WEIGHTS["country"] * country_score
        + _WEIGHTS["references"] * ref_score
        + _WEIGHTS["presence"] * presence
        + _WEIGHTS["languages"] * lang_score
    )
    score = round(weighted / sum(_WEIGHTS.values()) * 100, 1)

    manual = bool(profile.guardrail) or not profile.country_confirmed or bool(
        {"tech_focus", "services", "client_references"} & set(profile.fields_unspecified)
    )

    if score >= 70:
        grade = "STRONG PARTNER FIT"
    elif score >= 55:
        grade = "POSSIBLE PARTNER"
    elif score >= 40:
        grade = "WEAK PARTNER"
    else:
        grade = "POOR PARTNER FIT"
    if manual:
        grade = f"(REVIEW) {grade}"

    return score, grade, manual


def qualify(company: ESNCompany, profile: ESNProfile, pages_analyzed: int) -> QualifiedPartner:
    score, grade, manual = compute_affinity(profile, company.country, pages_analyzed)

    reason = ""
    if profile.tech_focus in ("low_code_reseller", "proprietary_reseller"):
        reason = (
            "direct competitor: exclusively resells proprietary / low-code products "
            "with no custom development capability"
        )

    qualified = bool(not reason and score >= config.AFFINITY_THRESHOLD)

    return QualifiedPartner(
        partner_id=company.id,
        company_name=profile.company_name or company.name,
        country=company.country,
        website=profile.website or company.website,
        contact_url=profile.contact_url,
        size=profile.employees_estimate or ("" if profile.project_scale == "unspecified" else profile.project_scale),
        project_scale=profile.project_scale,
        services=profile.services,
        client_references=profile.client_references,
        languages=profile.languages,
        tech_focus=profile.tech_focus,
        affinity_score=score,
        affinity_grade=grade,
        qualified=qualified,
        disqualification_reason=reason,
        requires_manual_review=manual,
        pages_analyzed=pages_analyzed,
        source=company.source,
        profile=profile.model_dump(mode="json"),
    )
