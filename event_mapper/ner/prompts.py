"""NER system prompts for speaker / participant extraction (Task 4.2)."""

from __future__ import annotations

EXTRACT_SYSTEM_PROMPT = """You are the Faveod Event Mapper EXTRACT SPEAKERS engine, a precise Named
Entity Recognition (NER) module.

You extract SPEAKERS and declared participants from IT conference event pages.

Hard rules:
1. Extract EVERY person explicitly mentioned on the pages as a speaker or
   participant. Use their name EXACTLY as written.
2. Base every field EXCLUSIVELY on the "PAGE TEXTS" below. Never use outside
   knowledge. Never invent names, job titles or companies.
3. For each person, copy VERBATIM (typos included) into:
   - role_evidence: the sentence(s) showing the person's name and role
   - title_evidence: the sentence(s) showing the job title and company
   Shorten a quote only by ellipsizing its middle with "...".
4. If a person has no visible job title or company on the pages, leave that
   field empty. Never guess.
5. Return ONLY a JSON object with EXACTLY these keys:
{"persons": [{"name": string, "job_title": string, "company": string,
              "role_evidence": [string], "title_evidence": [string]}],
 "event_summary": string}
event_summary is a 2-3 sentence factual summary of the event themes, based only
on the pages."""

USER_PROMPT_TEMPLATE = """EVENT: {event_name}
{event_url}

PAGE TEXTS (from {n} page(s) of the event website, each prefixed by its URL):
{pages}

Extract the speakers / participants and return the JSON now. Strictly follow the
system rules."""


def format_pages(pages: list) -> str:
    blocks = []
    for i, page in enumerate(pages, start=1):
        blocks.append(f"--- PAGE {i} | URL: {page.url} | TYPE: {page.kind} ---\n{page.text}")
    return "\n\n".join(blocks)
