# Phase 4 — Agent 3 "Event Mapper & Lead Profiler": What Was Done & How to Run

> Short runbook for the work completed in this session.
> Full technical notes: `PHASE4_AGENT3_EVENT_MAPPER.md`.

---

## 1. What I did

Built **Agent 3 — "Event Mapper & Lead Profiler"** (`event_mapper/`), the third
agent of the Faveod sovereign multi-agent system, following the same conventions
as Agents 1 & 2 (LangGraph, shared OpenRouter LLM client, offline sample
fallbacks, strict anti-hallucination guardrails).

### Modules created (matching tasks 4.1 → 4.3)

| Module | Task | Purpose |
|--------|------|---------|
| `event_mapper/ingest/` | 4.1 | Event discovery backends: `ten_times`, `eventbrite`, `luma`, `news` (SearXNG) + offline sample corpus (4 regional IT conferences) + resilient registry with sample fallback |
| `event_mapper/scrape/` | 4.2 | Fetches event pages (home + speakers/agenda/attendees), strips boilerplate, extracts clean text |
| `event_mapper/ner/` | 4.2 | LLM Named Entity Recognition: extracts speakers with **verbatim-evidence guardrails** (name must appear on the page; role/title quotes must match word-for-word) |
| `event_mapper/leads/` | 4.3 | Deterministic decision-maker/seniority classifier, LLM key-challenges summary (evidence-verified or honestly empty), weighted lead score + priority |
| `event_mapper/pipeline.py` | — | Per-event orchestration: scrape → NER → classify → enrich → score |
| `event_mapper/graph.py` | — | LangGraph graph: `collect_events` → `Send` fan-out, one parallel branch per event |
| `event_mapper/output/writer.py` | 4.3 | Writes `events.jsonl`, `leads.jsonl`, `leads_latest.json`, `priority_leads.json` |
| `tests/test_event_mapper.py` | — | 7 pytest-free tests (role classification, evidence guardrail, LLM-unavailable fallback, content-too-thin honesty, scoring, offline pipeline, graph fan-out) |

### Bugs found & fixed during verification
1. `"cto"` was matching inside the word `"director"` → added word-boundary
   matching for acronyms (`\bcto\b`, `\bcio\b`, …).
2. `"Chief Information Security Officer"` was not classified as C-level → added
   the full phrase to the classifier.

### Other files updated
- `tasks.md` — Tasks 4.1, 4.2, 4.3 marked ✅.
- `.env.example` — new Agent 3 block (`EVENT_SOURCE`, `EVENT_COUNTRIES`,
  `EVENT_KEYWORDS`, `PRIORITY_THRESHOLD`, …).
- `docker-compose.yml` — new `event-mapper` service.
- `Dockerfile` — copies the `event_mapper` package.
- `README.md` — Agent 3 section, layout, run commands, tests, config table.
- Installed missing deps (`beautifulsoup4`, `lxml`, `openai`, …) from
  `requirements.txt`.

---

## 2. How it works (in one paragraph)

The CLI discovers IT events in the target markets (or loads the offline sample
corpus), then for each event the LangGraph graph fans out a parallel branch that
fetches the event pages, extracts speaker names/titles/companies via LLM NER
(every claim verified verbatim against the page text), classifies each person as
a decision-maker or not (government / C-level / director / manager / engineer),
summarizes their key IT challenges from panel topics (evidence-verified), and
computes a **lead score (0–100%)** with a priority bucket. Only evidence-backed
facts survive; anything unverifiable is flagged `requires_manual_review`.

---

## 3. How to run

Requirement: Python 3.12+ and `pip install -r requirements.txt` (deps already
installed in this session).

### 3.1 Offline demo (no keys, no network)
```powershell
python -m event_mapper run --source sample
```
Expected output: `4 event(s)`, `12 lead(s)`, 6 of them `HIGH PRIORITY`
(decision-makers such as Aminata Diallo 90%, Karim Benali 90%, Fahad Al-Otaibi
90%, Sarah Mensah 86%, Mona Ghali 86%, Dr. Layla Haddad 85%).

### 3.2 Live event discovery (needs network; optional keys)
```powershell
python -m event_mapper run --source ten_times
python -m event_mapper run --source eventbrite
python -m event_mapper run --source luma
docker compose up searxng          # then:
python -m event_mapper run --source news
```

### 3.3 Real LLM scoring (recommended)
Copy `.env.example` to `.env` and set `OPENROUTER_API_KEY` (free tier is fine).
Without a key everything still runs, but extraction/enrichment stays in
guardrail-only (manual review) mode.

### 3.4 Scoped runs
```powershell
python -m event_mapper run --countries Morocco Senegal Egypt --limit 10
python -m event_mapper sources     # list event backends
python -m event_mapper run --source news --interval 60   # rescan hourly
```

### 3.5 Tests (all three agents)
```powershell
python tests\test_guardrails.py     # Agent 1  -> ALL GUARDRAIL TESTS PASSED
python tests\test_partner_scout.py  # Agent 2  -> ALL PARTNER SCOUT TESTS PASSED
python tests\test_event_mapper.py   # Agent 3  -> ALL EVENT MAPPER TESTS PASSED
```

### 3.6 Docker (everything)
```powershell
docker compose --profile app up     # Qdrant + SearXNG + tender-hunter + partner-scout + event-mapper
```

---

## 4. Outputs (in `data/output/`)

| File | Contents |
|------|----------|
| `events.jsonl` | append-only history of discovered events |
| `events_latest.json` | last run's events |
| `leads.jsonl` | append-only history of every lead |
| `leads_latest.json` | last run, sorted by lead score |
| `priority_leads.json` | only leads scoring ≥ `PRIORITY_THRESHOLD` (70) |

Sample prospect card (abridged):
```json
{
  "lead_id": "EV-2026-001-605559",
  "person_name": "Aminata Diallo",
  "job_title": "Chief Information Officer",
  "company": "Ministry of Digital Economy of Senegal",
  "country": "Senegal",
  "seniority": "c_level",
  "decision_maker": true,
  "event_name": "Digital Transformation Africa Summit",
  "lead_score": 90.0,
  "priority": "HIGH PRIORITY",
  "requires_manual_review": false,
  "person": { "verified": true }
}
```

---

## 5. Status summary

- ✅ Agent 3 built end-to-end and verified with a real free LLM.
- ✅ 7/7 new tests pass; no regressions (Agent 1: 6/6, Agent 2: 8/8).
- ✅ All modules compile; `tasks.md` 4.1–4.3 marked done.
- ▶ Next phase: **Phase 5** — dashboard merging tender feed + partner directory +
  event prospect lists with alerts.
