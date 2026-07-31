"""Faveod Fit Score computation (Task 2.4)."""

from __future__ import annotations

from tender_hunter.models import GUARDRAIL, CriterionResult

WEIGHTS = {
    "ip_ownership": 0.35,
    "security_quality": 0.30,
    "timeline": 0.20,
    "green_it": 0.15,
}

VERDICT_VALUES = {
    "SATISFIED": 1.0,
    "PARTIAL": 0.5,
    "NOT_SATISFIED": 0.0,
}


def compute_fit_score(criteria: list[CriterionResult]) -> tuple[float, str, bool]:
    """Return (fit_score 0-100, grade, requires_manual_review)."""
    specified = [c for c in criteria if c.status in VERDICT_VALUES]
    manual = any(c.status == GUARDRAIL for c in criteria)

    if not specified:
        return 0.0, "POOR FIT", manual

    weight_sum = sum(WEIGHTS.get(c.criterion, 0.0) for c in specified)
    if weight_sum == 0:
        return 0.0, "POOR FIT", manual

    score = sum(WEIGHTS.get(c.criterion, 0.0) * VERDICT_VALUES[c.status] for c in specified) / weight_sum * 100
    score = round(score, 1)

    if score >= 80:
        grade = "STRONG FIT"
    elif score >= 60:
        grade = "POSSIBLE FIT"
    elif score >= 40:
        grade = "WEAK FIT"
    else:
        grade = "POOR FIT"

    if manual:
        grade = f"(REVIEW) {grade}"
    return score, grade, manual


def build_summary(criteria: list[CriterionResult]) -> str:
    parts = []
    for c in criteria:
        sim = f"{c.similarity_score:.2f}"
        parts.append(f"{c.label}: {c.status} (sim {sim})")
    header = " | ".join(parts)
    manual = any(c.status == GUARDRAIL for c in criteria)
    tail = "Manual review required for unspecified criteria." if manual else "No manual review required."
    return f"{header}. {tail}"
