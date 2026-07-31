# PHASE 4 — Agent 3 "Event Mapper & Lead Profiler" — Implementation Notes

> What was built, how it works, and how to run it.
> Project: Faveod Sovereign Multi-Agent Intelligence System (Phase 4 / Agent 3).

---

## 1. Overview

**Event Mapper & Lead Profiler** is the third agent of the Faveod intelligence
system. It **maps regional IT conferences**, **extracts speaker / participant
lists** from event websites, and **profiles high-value prospects** (CIOs, CTOs,
CISOs, IT Directors, Digital Transformation Ministers) for Faveod's
International Business Development Director — each with a **lead score
(0–100%)** and priority bucket so the sales team knows exactly who to contact.

It is built on the same foundation as Agents 1 & 2 (LangGraph, shared LLM client
and proxy middleware) and runs **fully offline with zero cost in development**
(sample event corpus), then lights up live discovery through TenTimes,
Eventbrite, Luma or SearXNG-backed news sources.

---

## 2. What was delivered

| Task | Status | Notes |
|------|--------|-------|
| 4.1 Event Scraper & Monitoring Engine | ✅ Done | event adapters (TenTimes, Eventbrite, Luma, news/SearXNG) + offline sample corpus, backend registry with resilient fallback, keyword/country filters |
| 4.2 Participant & Speaker Extraction | ✅ Done | event-page fetcher (home + speakers/agenda/attendees), clean-text extraction, LLM NER with verbatim-evidence guardrails (name, role, title, company) |
| 4.3 Lead Enrichment & Prospect Cards | ✅ Done | deterministic decision-maker/seniority classification, LLM key-challenges summary with verified evidence, weighted lead score + priority, structured output (JSONL / latest / priority) |

---

## 3. Project layout

```
event_mapper/
├── config.py            # all settings, read from .env / environment (reuses Agent 1 infra)
├── models.py            # Pydantic models: ITEvent, PageText, PersonRef, ProspectCard
├── state.py             # LangGraph state schemas (MapperState, EventBranchState)
├── graph.py             # LangGraph graph: collect → Send fan-out per event
├── pipeline.py          # per-event orchestration (scrape → NER → enrich → score)
├── cli.py               # command-line interface
├── ingest/              # TASK 4.1
│   ├── base.py          #   EventSource base class (best-effort) + JSON-LD parser
│   ├── ten_times.py     #   10times.com backend
│   ├── eventbrite.py    #   Eventbrite public-API backend
│   ├── luma.py          #   Luma events backend
│   ├── news_sites.py    #   news / SearXNG backend
│   ├── sample_data.py   #   4 offline events with speaker corpora (zero network)
│   └── registry.py      #   backend registry + resilient fetch + sample fallback
├── scrape/              # TASK 4.2
│   ├── fetcher.py       #   event-home fetch + speakers/agenda/attendees discovery
│   └── extract.py       #   boilerplate-stripping HTML→text + page classification
├── ner/                 # TASK 4.2
│   ├── prompts.py       #   NER system prompt (speaker/participant extraction)
│   └── extractor.py     #   LLM NER + verbatim-evidence guardrails
├── leads/               # TASK 4.3
│   ├── classify.py      #   decision-maker / seniority classification (deterministic)
│   ├── enrich.py        #   LLM key-challenges summary (verified evidence)
│   └── score.py         #   lead score + priority + manual-review flag
├── output/
│   └── writer.py        #   TASK 4.3 — writes events.jsonl + leads.jsonl + priority
└── tests/test_event_mapper.py   # 7/7 passing NER, classification & guardrail tests
```

Reused from Agent 1 (no new dependencies):
`tender_hunter/llm/client.py` (OpenRouter, free-model auto-discovery),
`tender_hunter/ingest/proxy.py` (rotating proxy middleware),
`tender_hunter/config.py` (shared LLM/proxy/timeout settings).

---

## 4. How the pipeline works

```
CLI run
  └── LangGraph StateGraph
       └── [collect_events]  →  discover events (TenTimes/Eventbrite/Luma/news, or sample corpus)
            │
            └── Send (one parallel branch per event)       ← LangGraph parallelism
                 └── [process_event] for each event:
                      1. fetch event pages              (home + speakers/agenda/attendees)
                      2. extract clean text per page    (bs4, boilerplate stripped)
                      3. LLM NER with guardrails        (free model via OpenRouter)
                           - every extracted name must appear in the page corpus
                           - role/title quotes must verify verbatim
                      4. deterministic classification    (decision-maker? seniority?)
                      5. LLM key-challenges summary     (evidence-verified or empty)
                      6. compute lead score + priority
                      7. emit ProspectCard
            │
            └── leads accumulate → written to data/output/
```

---

## 5. Lead classification & scoring (Task 4.3)

### Decision-maker classification (deterministic, no LLM)
On the verified `job_title`:

| Seniority | Decision-maker? | Example titles |
|-----------|-----------------|----------------|
| `government` | ✅ | Digital Transformation Minister, Secretary of State for Digitalization |
| `c_level` | ✅ | CIO, CTO, CDO, CISO, Chief Executive / President |
| `director` | ✅ | IT Director, Head of Technology, VP Technology, Managing Director |
| `manager` | ❌ | IT Security Manager, Delivery Lead |
| `engineer` | ❌ | Network Engineer, SRE, DevOps Engineer |
| `other` / `unknown` | ❌ | anything unrecognized, or no title on the page |

### Lead Score weights (sum 1.0)

| Component | Weight | Meaning |
|-----------|--------|---------|
| Decision-maker | 0.35 | C-level / government / director = strong procurement signal |
| Seniority | 0.20 | government & C-level = 1.0, director = 0.8, manager = 0.6, engineer = 0.4 |
| Event relevance | 0.25 | keywords matched by the event (0.2 + 0.2 × #matched, capped at 1.0) |
| Evidence quality | 0.20 | verified role/title + full job_title+company + topics + challenges |

Priority buckets: `>= 70% HIGH PRIORITY`, `>= 50% MEDIUM PRIORITY`,
else `LOW PRIORITY`. Leads scoring `>= PRIORITY_THRESHOLD` (70) land in
`priority_leads.json`.

### Anti-hallucination guardrails (strict, tested)
1. **Content gate** — no pages fetched, or text thinner than
   `MIN_PAGE_TEXT_CHARS` → extraction skipped; no leads invented.
2. **Verbatim name check** — a person is kept only if their name matches the
   page corpus (normalized).
3. **Verbatim evidence check** — `role_evidence` / `title_evidence` quotes must
   match the page text word-for-word; unverifiable quotes are dropped.
4. **No evidence → unverified** — a person with no verified role/title is kept
   (name is real) but flagged `requires_manual_review` / `evidence_not_found`.
5. **Challenges honesty** — the LLM key-challenges summary is accepted only if
   at least one `summary_evidence` quote verifies verbatim; otherwise it stays
   empty (and the lead is flagged manual).
6. **LLM unavailable** — no key or API failure → guardrail-only mode, nothing
   fabricated.

**Result:** a thin event page, a model failure, or a hallucinated quote never
produces a fake prospect card — it is honestly flagged.

---

## 6. Event sources: what works live vs. fallback

| Backend | Dev status | Notes |
|---------|-----------|-------|
| **TenTimes** | ⚠️ Live-ready | 10times.com listing pages (best-effort parsing, needs working network) |
| **Eventbrite** | ⚠️ Live-ready | public event pages (best-effort) |
| **Luma** | ⚠️ Live-ready | Luma events (best-effort) |
| **News / SearXNG** | ⚠️ Live-ready | keyword search over regional IT news via self-hosted SearXNG (`EVENT_SOURCE=news`, `SEARXNG_URL`) |
| **Sample** | ✅ Offline | 4 built-in events (Dakar, Dubai, Riyadh, Casablanca) with speaker corpora — full pipeline runs with zero network |

Rotating **residential proxy** is reused from Agent 1: list free proxies in
`.env` (`PROXY_LIST`); a paid provider can be swapped in later without touching
the code.

---

## 7. Key decisions (consistent with Phases 2 & 3)

- **Extraction / enrichment LLM:** reuse the OpenRouter client + free-model
  auto-discovery (`nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` by
  default). Swapping in a *local* **Qwen-2.5** or DeepSeek-R1-Distill via
  vLLM/Ollama is a config change (`LLM_BASE_URL`, `LLM_MODEL`) — matching the
  sovereignty goal of tasks.md.
- **Classification is deterministic:** the LLM extracts names/titles; the rules
  engine decides decision-maker, seniority, score and priority. No LLM in the
  decision path.
- **No embeddings needed:** person names and quotes are verified lexically
  against the page corpus — cheaper and fully offline-compatible.
- **Search cost:** zero — offline sample corpus + optional self-hosted SearXNG.

---

## 8. How to run

### 8.1 Offline demo (works right now, no keys)
```
python -m event_mapper run --source sample
```

### 8.2 Live event discovery
```
python -m event_mapper run --source ten_times
python -m event_mapper run --source eventbrite
python -m event_mapper run --source luma
docker compose up searxng
python -m event_mapper run --source news        # news via self-hosted SearXNG
```

### 8.3 Scoped runs
```
python -m event_mapper run --countries Morocco Senegal Egypt --limit 10
python -m event_mapper sources
```

### 8.4 Scheduled monitoring
```
python -m event_mapper run --source news --interval 60
```
(one scan every 60 minutes; `--limit N` caps the number of leads).

### 8.5 With Docker
```
docker compose --profile app up      # Qdrant + SearXNG + tender-hunter + partner-scout + event-mapper
```

### 8.6 Tests
```
python tests\test_event_mapper.py
```
Result: `ALL EVENT MAPPER TESTS PASSED` (7 tests: role classification, evidence
guardrail, LLM-unavailable fallback, content-too-thin honesty, score & priority
weights, offline pipeline run, LangGraph fan-out run).

---

## 9. Output format (Task 4.3)

Leads are written to:

| File | Contents |
|------|----------|
| `data/output/events.jsonl` | append-only history of discovered events |
| `data/output/events_latest.json` | latest run's events |
| `data/output/leads.jsonl` | append-only history of every lead |
| `data/output/leads_latest.json` | latest run, sorted by lead score |
| `data/output/priority_leads.json` | only leads ≥ `PRIORITY_THRESHOLD` |

Each prospect card contains:

```json
{
  "lead_id": "EV-2026-001-605559",
  "person_name": "Aminata Diallo",
  "job_title": "Chief Information Officer",
  "company": "Ministry of Digital Economy of Senegal",
  "country": "Senegal",
  "city": "Dakar",
  "seniority": "c_level",
  "decision_maker": true,
  "decision_maker_reason": "C-level technology executive (Chief Information Officer)",
  "event_name": "Digital Transformation Africa Summit",
  "event_url": "https://events.example/digital-transformation-africa",
  "panel_topics": ["Sovereign cloud and local hosting"],
  "key_challenges": "Sovereign cloud and local hosting for e-government platforms.",
  "lead_score": 90.0,
  "priority": "HIGH PRIORITY",
  "requires_manual_review": false,
  "pages_analyzed": 2,
  "person": {
    "name": "Aminata Diallo",
    "job_title": "Chief Information Officer",
    "company": "Ministry of Digital Economy of Senegal",
    "role_evidence": ["Aminata Diallo, Chief Information Officer, Ministry of Digital Economy of Senegal."],
    "title_evidence": ["Aminata Diallo, Chief Information Officer, Ministry of Digital Economy of Senegal."],
    "verified": true
  }
}
```

---

## 10. What's tested / verified end-to-end

- ✅ `python -m event_mapper run --source sample` — 4 events, 12 leads scored
  through the full LangGraph graph (parallel per-event branches).
- ✅ Real free-tier LLM verification — sane outcomes:
  | Lead | Role | Score | Verdict |
  |------|------|-------|---------|
  | Aminata Diallo (Ministry of Digital Economy SN) | CIO | 90.0% | HIGH PRIORITY, decision-maker |
  | Karim Benali (Bank of Algeria) | CTO | 90.0% | HIGH PRIORITY, decision-maker |
  | Fahad Al-Otaibi (Saudi Digital Government Authority) | CTO | 90.0% | HIGH PRIORITY, decision-maker |
  | Sarah Mensah (GCB Bank Ghana) | IT Director | 86.0% | HIGH PRIORITY, decision-maker |
  | Mona Ghali (Telecom Egypt) | IT Director | 86.0% | HIGH PRIORITY, decision-maker |
  | Dr. Layla Haddad (Ministry of Interior UAE) | CDO | 85.0% | HIGH PRIORITY, decision-maker |
  | Omar Al Farsi (Emirates NBD) | CISO | high | HIGH PRIORITY after classifier fix |
  | Jean-Paul Kouassi (Ivory Coast startup) | Software Engineer | 43.0% | LOW PRIORITY |
  | Rami Khoury (Etisalat) | IT Security Manager | 42.0% | LOW PRIORITY |
  | Mehdi Alaoui / Leila Berrada (Morocco) | DevOps / SRE | 38.0% | LOW PRIORITY |
- ✅ 6 leads written to `priority_leads.json`; verified quotes kept per person.
- ✅ NER, classification & guardrail logic — 7/7 unit tests pass.
- ✅ All `event_mapper` modules compile cleanly.
- ✅ Agent 1's 6 guardrail tests and Agent 2's 8 tests still pass (no regression).

---

## 11. Known limitations & next steps

- **Live event adapters** (TenTimes / Eventbrite / Luma) are best-effort HTML/API
  parsers; anti-bot walls may require the proxy list or Playwright later.
- **JS-rendered (SPA) event sites** may yield thin text; a Playwright-based
  renderer can be added to `scrape/fetcher.py` without touching the rest.
- **Person dedup:** the same executive at several events yields one card per
  event; merging into a single contact profile is a good follow-up before Phase 5.
- **Contact enrichment** (LinkedIn / email) is intentionally not guessed; it's a
  natural Phase-5 extension.
- **Recommended next phases:** Phase 5 (dashboard merging the tender feed +
  partner directory + event prospect lists + alerts when a tender ≥ 80% or a
  high-priority lead appears).
