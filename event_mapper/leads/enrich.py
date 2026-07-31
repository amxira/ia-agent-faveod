"""LLM lead enrichment: key IT challenges from panel topics (Task 4.3).

The challenges summary is only accepted if at least one of the model's quotes
verifies verbatim against the event pages; otherwise it is left empty (manual
review) instead of hallucinated.
"""

from __future__ import annotations

import logging
import re

from event_mapper.models import ITEvent, PageText, PersonRef
from tender_hunter.llm.client import LLMClient

log = logging.getLogger(__name__)

_MIN_EVIDENCE_CHARS = 8

ENRICH_SYSTEM_PROMPT = """You are the Faveod Event Mapper LEAD CHALLENGES engine.

Given a lead's profile (person + company) and the event pages, summarize the
lead's likely key IT challenges based ONLY on what the pages state: their
session, panel topics, or the event themes they are associated with.

Hard rules:
1. Base everything EXCLUSIVELY on the "PAGE TEXTS". Never use outside knowledge.
2. For every claim, copy the supporting text VERBATIM into summary_evidence.
3. If the pages contain nothing relevant to this person, leave `challenges`
   empty and `summary_evidence` empty. Never guess.
4. `confidence` is your overall certainty, from 0.0 to 1.0.
5. Return ONLY a JSON object with EXACTLY these keys:
{"challenges": string, "topics": [string], "summary_evidence": [string], "confidence": float}"""

USER_PROMPT_TEMPLATE = """LEAD:
- Name: {name}
- Job title: {job_title}
- Company: {company}
- Event: {event_name} ({event_url})

PAGE TEXTS (from the event website):
{pages}

Summarize this lead's key IT challenges and return the JSON now. Strictly follow
the system rules."""


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().lower()


def enrich(person: PersonRef, event: ITEvent, pages: list[PageText], llm: LLMClient) -> tuple[str, list[str]]:
    if not pages or not llm.available:
        return "", []

    corpus_blob = _normalize(" ".join(page.text for page in pages))
    if len(corpus_blob) < 80:
        return "", []

    user_prompt = USER_PROMPT_TEMPLATE.format(
        name=person.name,
        job_title=person.job_title or "unknown",
        company=person.company or "unknown",
        event_name=event.name,
        event_url=event.url,
        pages="\n\n".join(f"--- {p.url} ---\n{p.text}" for p in pages),
    )
    raw = llm.chat_json(ENRICH_SYSTEM_PROMPT, user_prompt)
    if raw is None:
        return "", []

    verified = [
        str(q).strip()[:600] for q in (raw.get("summary_evidence") or [])
        if len(str(q).strip()) >= _MIN_EVIDENCE_CHARS
        and (_normalize(str(q)) in corpus_blob or corpus_blob in _normalize(str(q)))
    ]
    if not verified:
        return "", []

    challenges = str(raw.get("challenges") or "").strip()[:2000]
    topics = [str(t).strip()[:300] for t in (raw.get("topics") or []) if str(t).strip()][:10]
    return challenges, topics
