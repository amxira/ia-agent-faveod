"""Lead scoring & priority (Task 4.3). Deterministic on verified facts."""

from __future__ import annotations

from event_mapper.models import ITEvent, PersonRef, ProspectCard

_WEIGHTS = {
    "decision": 0.35,
    "seniority": 0.20,
    "relevance": 0.25,
    "evidence": 0.20,
}
_SENIORITY_VALUE = {
    "government": 1.0,
    "c_level": 1.0,
    "director": 0.8,
    "manager": 0.6,
    "engineer": 0.4,
    "other": 0.3,
    "unknown": 0.0,
}


def compute_lead_score(
    decision_maker: bool,
    seniority: str,
    event: ITEvent,
    person: PersonRef,
    challenges: str,
    topics: list[str],
) -> tuple[float, str, bool]:
    decision = 1.0 if decision_maker else 0.0
    seniority_value = _SENIORITY_VALUE.get(seniority, 0.0)
    relevance = min(1.0, 0.2 + 0.2 * len(event.keywords_matched))

    evidence = 0.0
    if person.verified:
        evidence += 0.5
    if person.job_title and person.company:
        evidence += 0.2
    if topics:
        evidence += 0.15
    if challenges:
        evidence += 0.15
    evidence = min(evidence, 1.0)

    weighted = (
        _WEIGHTS["decision"] * decision
        + _WEIGHTS["seniority"] * seniority_value
        + _WEIGHTS["relevance"] * relevance
        + _WEIGHTS["evidence"] * evidence
    )
    score = round(weighted / sum(_WEIGHTS.values()) * 100, 1)

    if score >= 70:
        priority = "HIGH PRIORITY"
    elif score >= 50:
        priority = "MEDIUM PRIORITY"
    else:
        priority = "LOW PRIORITY"

    manual = (not person.verified) or (not person.job_title) or (not person.company) or not challenges
    return score, priority, manual


def build_prospect_card(
    person: PersonRef,
    event: ITEvent,
    pages_analyzed: int,
    decision_maker: bool,
    seniority: str,
    reason: str,
    challenges: str,
    topics: list[str],
) -> ProspectCard:
    score, priority, manual = compute_lead_score(decision_maker, seniority, event, person, challenges, topics)
    return ProspectCard(
        lead_id=f"{event.id}-{abs(hash(person.name)) % 10**6:06d}",
        person_name=person.name,
        job_title=person.job_title,
        company=person.company,
        country=event.country,
        city=event.city,
        seniority=seniority,
        decision_maker=decision_maker,
        decision_maker_reason=reason,
        event_name=event.name,
        event_url=event.url,
        panel_topics=topics,
        key_challenges=challenges,
        lead_score=score,
        priority=priority,
        requires_manual_review=manual,
        pages_analyzed=pages_analyzed,
        source=event.source,
        person=person.model_dump(mode="json"),
    )
