"""NER speaker extraction with anti-hallucination guardrails (Task 4.2).

A person is kept only if their name appears in the page corpus AND at least one
of their quotes verifies verbatim. Names with no verified role/title context are
still kept with whatever verified context exists; completely unverifiable
persons are dropped.
"""

from __future__ import annotations

import logging
import re

from event_mapper import config
from event_mapper.models import GUARDRAIL, ITEvent, PageText, PersonRef
from event_mapper.ner.prompts import EXTRACT_SYSTEM_PROMPT, USER_PROMPT_TEMPLATE, format_pages
from tender_hunter.llm.client import LLMClient

log = logging.getLogger(__name__)

_MIN_EVIDENCE_CHARS = 6


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().lower()


class SpeakerExtractor:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def extract(self, event: ITEvent, pages: list[PageText]) -> list[PersonRef]:
        if not pages:
            log.info("[%s] no pages to extract from", event.id)
            return []

        corpus_blob = " ".join(page.text for page in pages)
        if len(corpus_blob) < config.MIN_PAGE_TEXT_CHARS:
            log.info("[%s] content too thin for extraction", event.id)
            return []

        if not self.llm.available:
            log.warning("[%s] no LLM; NER skipped", event.id)
            return []

        user_prompt = USER_PROMPT_TEMPLATE.format(
            event_name=event.name,
            event_url=event.url,
            n=len(pages),
            pages=format_pages(pages),
        )
        raw = self.llm.chat_json(EXTRACT_SYSTEM_PROMPT, user_prompt)
        if raw is None:
            log.warning("[%s] LLM returned nothing; NER skipped", event.id)
            return []

        blob_norm = _normalize(corpus_blob)
        persons: list[PersonRef] = []
        seen: set[str] = set()
        for item in raw.get("persons") or []:
            if not isinstance(item, dict):
                continue
            name = _normalize(str(item.get("name") or "")).strip()
            if len(name) < 3 or name not in blob_norm:
                continue  # name must be verbatim in the corpus
            display = str(item.get("name") or "").strip()

            role_ok = [q.strip()[:400] for q in (item.get("role_evidence") or []) if _verified(q, blob_norm)]
            title_ok = [q.strip()[:400] for q in (item.get("title_evidence") or []) if _verified(q, blob_norm)]

            key = name
            if key in seen:
                continue
            seen.add(key)

            person = PersonRef(
                name=display or str(item.get("name") or ""),
                job_title=_clean_scalar(item.get("job_title")),
                company=_clean_scalar(item.get("company")),
                role_evidence=role_ok,
                title_evidence=title_ok,
                verified=bool(role_ok or title_ok),
                guardrail=None if (role_ok or title_ok) else "evidence_not_found",
            )
            persons.append(person)

        log.info("[%s] extracted %d person(s)", event.id, len(persons))
        return persons


def _verified(quote, blob_norm: str) -> bool:
    quote = (quote or "").strip()
    if len(quote) < _MIN_EVIDENCE_CHARS:
        return False
    qnorm = _normalize(quote)
    return qnorm in blob_norm or blob_norm in qnorm


def _clean_scalar(value) -> str:
    text = str(value or "").strip()
    return text[:300] if text else ""
