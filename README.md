# Faveod Sovereign Multi-Agent Intelligence System

100% sovereign, self-hosted multi-agent AI system for Faveod's International
Business Development: it finds **software tenders** (Agent 1), discovers local
**IT partner companies** (Agent 2), and maps **events & leads** (Agent 3) across
Africa and the Middle East.

Built with Python + LangGraph. No paid APIs in dev: free OpenRouter reasoning
models, Google Gemini free-tier embeddings, self-hosted SearXNG, and an offline
sample corpus so everything runs with zero network.

---

## What has been done

### Agent 1 — "Tender Hunter" (`tender_hunter/`) — Phase 2 ✅

Scrapes international software tenders (World Bank, EBRD; AfDB/IMF adapters
ready), parses PDFs/DOCX, chunks and embeds them, then scores each tender against
the **4 Faveod criteria** with strict anti-hallucination guardrails:

1. Source Code / IP Ownership
2. High Security / Quality
3. Compressed Timelines
4. Green-IT

Per criterion the engine retrieves the most relevant chunks, and only if embedding
similarity ≥ `SIMILARITY_THRESHOLD` (0.75) is the LLM consulted. Every quote the
LLM returns is cross-checked verbatim against the document; unverifiable claims
are dropped and the criterion is flagged `Manual review required` — the engine
never guesses.

Output: `FaveodReport` with a **Faveod Fit Score (0–100%)**, grade, and page-level
citations.

### Agent 2 — "Partner Scout" (`partner_scout/`) — Phase 3 ✅

Identifies local IT services companies (ESNs / integrators) in target countries
that could act as local implementation or support partners for Faveod.

Pipeline per company: **search** (self-hosted SearXNG, or offline sample corpus)
→ **website & portfolio fetch** (homepage + Case-Studies / References / Partners
pages) → **LLM profiling with guardrails** (tech focus, client references, project
scale, languages, contact — every claim must quote the company's own pages
verbatim) → **deterministic qualification** (direct competitors that only resell
SAP/Oracle/low-code products are excluded) with a weighted **Faveod Affinity
Score (0–100%)**.

Output: `QualifiedPartner` profiles in a partner directory.

### Agent 3 — "Event Mapper & Lead Profiler" (`event_mapper/`) — Phase 4 ✅

Maps regional IT conferences, extracts speaker / participant lists from event
websites, and profiles high-value prospects (CIOs, CTOs, CISOs, IT Directors,
Digital Transformation Ministers).

Pipeline per event: **discover** (TenTimes / Eventbrite / Luma / news via
SearXNG, or offline sample corpus) → **page fetch** (home + speakers/agenda/
attendees) → **LLM NER with guardrails** (every extracted name must appear in the
page corpus; role/title quotes must verify verbatim) → **deterministic
classification** (decision-maker? seniority?) → **LLM key-challenges summary**
(evidence-verified or honestly empty) → weighted **lead score (0–100%)** and
priority bucket.

Output: `ProspectCard` leads in `leads.jsonl` / `leads_latest.json` /
`priority_leads.json`.

### Shared infrastructure

All three agents reuse the same modules:

- `tender_hunter/llm/client.py` — OpenAI-compatible client for
  OpenRouter. If the configured free model disappears (404), it auto-discovers a
  working free model. Swap to a local Qwen-2.5 / DeepSeek-R1-Distill via vLLM or
  Ollama by changing `LLM_BASE_URL` + `LLM_MODEL` (sovereign option).
- `tender_hunter/embedding/` — Gemini free-tier embedder (with throttle/retry) +
  local hashing fallback.
- `tender_hunter/vectorstore/` — Qdrant (server or in-memory fallback).
- `tender_hunter/ingest/proxy.py` — rotating proxy middleware (free list in dev).
- LangGraph graph with `Send` fan-out for parallel per-item processing.

---

## Project layout

```
tender_hunter/                 # Agent 1 — Tender Hunter (Phase 2)
├── config.py models.py state.py graph.py pipeline.py cli.py
├── ingest/                    # world_bank, ebrd, afdb, imf, sample_data, proxy
├── parse/                     # PyMuPDF/DOCX extraction + chunking
├── embedding/ vectorstore/    # Gemini embedder + Qdrant store
├── reasoning/                 # criteria prompts + guardrail engine + fit score
├── llm/                       # OpenRouter client, free-model auto-discovery
└── output/                    # reports.jsonl / latest.json / high_value.json

partner_scout/                 # Agent 2 — Partner Scout (Phase 3)
├── config.py models.py state.py graph.py pipeline.py cli.py
├── search/                    # searxng backend + offline sample corpus
├── scrape/                    # website fetcher + HTML text extraction
├── analyze/                   # LLM company profiler + evidence guardrails
├── qualify/                   # competitor filter + Faveod Affinity Score
└── output/                    # partners.jsonl / partners_latest.json / qualified_partners.json

event_mapper/                  # Agent 3 — Event Mapper & Lead Profiler (Phase 4)
├── config.py models.py state.py graph.py pipeline.py cli.py
├── ingest/                    # ten_times, eventbrite, luma, news, sample corpus
├── scrape/                    # event page fetcher + HTML text extraction
├── ner/                       # LLM speaker NER + evidence guardrails
├── leads/                     # decision-maker classifier + enrichment + scoring
└── output/                    # events.jsonl / leads.jsonl / priority_leads.json

tests/                         # test_guardrails.py, test_partner_scout.py, test_event_mapper.py (pytest-free)
data/                          # sample_docs, downloads, output, logs
docker/searxng/settings.yml    # SearXNG config (JSON API enabled)
Dockerfile  docker-compose.yml  requirements.txt  .env.example
PHASE2_AGENT1_TENDER_HUNTER.md PHASE3_AGENT2_PARTNER_SCOUT.md PHASE4_AGENT3_EVENT_MAPPER.md  tasks.md
```

---

## Setup

```powershell
# 1. Create the virtual environment and install dependencies
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 2. Configure keys (free tiers only)
Copy-Item .env.example .env
# then edit .env and set:
#   OPENROUTER_API_KEY=sk-or-v1-...   (reasoning LLM, https://openrouter.ai)
#   GEMINI_API_KEY=...                (embeddings, https://aistudio.google.com/app/apikey)
# Leave LLM_MODEL as-is: the client auto-discovers a working free model.
```

Without any keys everything still runs: criteria/profiles are honestly held in
guardrail-only (manual review) mode instead of guessing.

---

## How to run

### Agent 1 — Tender Hunter

```powershell
# Offline demo (no network, no keys) — sample tenders in FR/AR/EN
.\.venv\Scripts\python.exe -m tender_hunter run --sources sample

# Full live run (World Bank + EBRD + sample)
.\.venv\Scripts\python.exe -m tender_hunter run --sources sample world_bank ebrd

# Scheduled monitoring (rescan every 60 min)
.\.venv\Scripts\python.exe -m tender_hunter run --sources sample world_bank ebrd --interval 60

# List sources / cap the number of reports
.\.venv\Scripts\python.exe -m tender_hunter sources
.\.venv\Scripts\python.exe -m tender_hunter run --limit 10
```

Outputs (in `data/output/`):
- `reports.jsonl` — full history, one report per line.
- `latest.json` — last run, sorted by Fit Score.
- `high_value.json` — tenders scoring ≥ 80%.

### Agent 2 — Partner Scout

```powershell
# Offline demo (sample companies, zero network)
.\.venv\Scripts\python.exe -m partner_scout run --source sample

# Live search: start self-hosted SearXNG, then
docker compose up searxng
.\.venv\Scripts\python.exe -m partner_scout run --source searxng

# Scoped to specific countries
.\.venv\Scripts\python.exe -m partner_scout run --countries Morocco Senegal Egypt --limit 12

# List search backends
.\.venv\Scripts\python.exe -m partner_scout sources
```

Outputs (in `data/output/`):
- `partners.jsonl` — full history.
- `partners_latest.json` — last run, sorted by Affinity Score.
- `qualified_partners.json` — only companies scoring ≥ `AFFINITY_THRESHOLD` (60)
  that are not disqualified competitors.

### Agent 3 — Event Mapper & Lead Profiler

```powershell
# Offline demo (sample events, zero network)
.\.venv\Scripts\python.exe -m event_mapper run --source sample

# Live event discovery (TenTimes / Eventbrite / Luma / news via SearXNG)
.\.venv\Scripts\python.exe -m event_mapper run --source ten_times
docker compose up searxng
.\.venv\Scripts\python.exe -m event_mapper run --source news

# Scoped to specific countries
.\.venv\Scripts\python.exe -m event_mapper run --countries Morocco Senegal Egypt --limit 10

# List event backends
.\.venv\Scripts\python.exe -m event_mapper sources
```

Outputs (in `data/output/`):
- `events.jsonl` / `events_latest.json` — discovered events.
- `leads.jsonl` — full lead history.
- `leads_latest.json` — last run, sorted by lead score.
- `priority_leads.json` — only leads scoring ≥ `PRIORITY_THRESHOLD` (70).

### Everything in Docker (Qdrant + SearXNG + all three agents)

```powershell
docker compose --profile app up
```

---

## Tests

```powershell
.\.venv\Scripts\python.exe tests\test_guardrails.py      # Agent 1  (6 tests)
.\.venv\Scripts\python.exe tests\test_partner_scout.py   # Agent 2  (8 tests)
.\.venv\Scripts\python.exe tests\test_event_mapper.py    # Agent 3  (7 tests)
```

All suites are pytest-free and assert against fakes (deterministic LLMs /
embeddings), covering: similarity gate, verbatim evidence verification,
hallucinated-quote suppression, invalid status, LLM-unavailable fallback, fit
score / affinity score / lead score formulas, competitor disqualification,
role classification, and offline end-to-end pipeline runs for each agent.

---

## Key configuration (.env)

| Variable | Default | Purpose |
|----------|---------|---------|
| `SOURCES` | `sample,world_bank,ebrd` | Agent 1 data sources |
| `SIMILARITY_THRESHOLD` | `0.75` | below this, criterion not evaluated by LLM |
| `SEARCH_SOURCE` | `sample` | Agent 2 backend (`sample` \| `searxng`) |
| `SEARXNG_URL` | `http://localhost:8080` | self-hosted meta-search |
| `TARGET_COUNTRIES` | Morocco, Senegal, Tunisia, Egypt, Saudi Arabia, UAE | Agent 2 markets |
| `AFFINITY_THRESHOLD` | `60` | min score to appear in `qualified_partners.json` |
| `EVENT_SOURCE` | `sample` | Agent 3 backend (`sample` \| `ten_times` \| `eventbrite` \| `luma` \| `news`) |
| `PRIORITY_THRESHOLD` | `70` | min lead score to appear in `priority_leads.json` |
| `QDRANT_URL` | *(empty)* | empty = in-memory vector store |

---

## Known limitations

- **World Bank / EBRD listings** have no downloadable PDFs, so live tenders stay
  in `[MANUAL REVIEW]` until a document-crawler pass fetches project procurement
  documents (planned next step for Agent 1).
- **AfDB / IMF** are blocked from the current network (403/404); adapters are
  ready and need no code changes once reachable.
- **SearXNG quality** depends on the engines enabled in the instance settings.
  JS-rendered (SPA) websites may yield thin text — a Playwright renderer can be
  added later.
- **Gemini free tier** throttles under heavy parallel embedding (429); the
  embedder retries with backoff and the graph degrades gracefully.
