"""Per-event pipeline: scrape -> NER extract -> enrich -> score each lead."""

from __future__ import annotations

import logging

from event_mapper import config
from event_mapper.leads.classify import classify_role
from event_mapper.leads.enrich import enrich
from event_mapper.leads.score import build_prospect_card
from event_mapper.models import ITEvent, ProspectCard
from event_mapper.ner.extractor import SpeakerExtractor
from event_mapper.scrape.fetcher import fetch_event_pages
from tender_hunter.llm.client import LLMClient

log = logging.getLogger(__name__)


class EventPipeline:
    def __init__(self, extractor: SpeakerExtractor, llm: LLMClient, proxy: dict | None = None):
        self.extractor = extractor
        self.llm = llm
        self.proxy = proxy

    def run(self, event: ITEvent) -> list[ProspectCard]:
        pages = fetch_event_pages(event, proxy=self.proxy)
        persons = self.extractor.extract(event, pages)
        if not persons:
            log.info("[%s] no persons extracted", event.id)
            return []

        cards: list[ProspectCard] = []
        for person in persons[: config.MAX_LEADS]:
            decision_maker, seniority, reason = classify_role(person.job_title)
            challenges, topics = enrich(person, event, pages, self.llm)
            card = build_prospect_card(
                person=person,
                event=event,
                pages_analyzed=len(pages),
                decision_maker=decision_maker,
                seniority=seniority,
                reason=reason,
                challenges=challenges,
                topics=topics,
            )
            log.info(
                "[%s] %s (%s @ %s) score=%.1f%% %s decision=%s manual=%s",
                card.lead_id,
                card.person_name,
                card.job_title,
                card.company,
                card.lead_score,
                card.priority,
                card.decision_maker,
                card.requires_manual_review,
            )
            cards.append(card)
        return cards
