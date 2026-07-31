# Faveod Intelligence System - Run & Test Guide

Everything you need to run the project and know what/how to test.
Project: Faveod Sovereign Multi-Agent Intelligence System (Phases 2-6).

---

## 1. Prerequisites

- Windows with Python 3.11+ (developed on 3.14).
- Optional keys (free tiers only). Without them everything still runs in
  guardrail-only mode:

| Key | Where to get it | Used for |
|-----|-----------------|----------|
| `OPENROUTER_API_KEY` | https://openrouter.ai | reasoning LLM (Agent analysis + chat agent) |
| `GEMINI_API_KEY` | https://aistudio.google.com/app/apikey | document embeddings (RAG) |

## 2. Setup (one time)

```powershell
# 1. Create virtual env and install dependencies
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 2. Configure keys
Copy-Item .env.example .env
# then edit .env and fill OPENROUTER_API_KEY and GEMINI_API_KEY
```

Optional date filters in `.env` (0 = disabled):

```ini
RECENT_DAYS=0        # Agent 1: keep only tenders published within last N days
UPCOMING_DAYS=0      # Agent 3: keep only events starting within next N days
```

> Tip: replace `.\.venv\Scripts\python.exe` with `python` below if your venv
> python is already on the PATH.

---

## 3. Run the agents (CLI)

### Agent 1 - Tender Hunter (`python -m tender_hunter`)

```powershell
# Offline demo (sample tenders in FR/AR/EN, no network, no keys)
.\.venv\Scripts\python.exe -m tender_hunter run --sources sample

# Live (World Bank + EBRD + sample)
.\.venv\Scripts\python.exe -m tender_hunter run --sources sample world_bank ebrd

# Date filter: only tenders published within the last 10 days
.\.venv\Scripts\python.exe -m tender_hunter run --sources sample --days 10

# Cap output / list available sources
.\.venv\Scripts\python.exe -m tender_hunter run --limit 10
.\.venv\Scripts\python.exe -m tender_hunter sources
```

Writes to `data/output/`: `reports.jsonl`, `latest.json`, `high_value.json`.

### Agent 2 - Partner Scout (`python -m partner_scout`)

```powershell
# Offline demo (sample companies, zero network)
.\.venv\Scripts\python.exe -m partner_scout run --source sample

# Live search via self-hosted SearXNG (start it first: docker compose up searxng)
.\.venv\Scripts\python.exe -m partner_scout run --source searxng

# Scoped to countries, capped
.\.venv\Scripts\python.exe -m partner_scout run --countries Morocco Senegal Egypt --limit 12
.\.venv\Scripts\python.exe -m partner_scout sources
```

Writes: `partners.jsonl`, `partners_latest.json`, `qualified_partners.json`.

### Agent 3 - Event Mapper & Lead Profiler (`python -m event_mapper`)

```powershell
# Offline demo
.\.venv\Scripts\python.exe -m event_mapper run --source sample

# Live backends (TenTimes / Eventbrite / Luma / news via SearXNG)
.\.venv\Scripts\python.exe -m event_mapper run --source ten_times
.\.venv\Scripts\python.exe -m event_mapper run --source news   # needs SearXNG up

# Only events starting within the next 30 days
.\.venv\Scripts\python.exe -m event_mapper run --source sample --days 30

.\.venv\Scripts\python.exe -m event_mapper run --countries Morocco Senegal --limit 10
.\.venv\Scripts\python.exe -m event_mapper sources
```

Writes: `events.jsonl`, `events_latest.json`, `leads.jsonl`,
`leads_latest.json`, `priority_leads.json`.

### Notifications (`python -m notifications`)

```powershell
.\.venv\Scripts\python.exe -m notifications check                # real dispatch
.\.venv\Scripts\python.exe -m notifications check --dry-run      # print only
.\.venv\Scripts\python.exe -m notifications check --reset        # re-alert after reset
.\.venv\Scripts\python.exe -m notifications check --interval 60  # scheduled
```

Channels are enabled by setting `NOTIFY_SLACK_WEBHOOK`,
`NOTIFY_TEAMS_WEBHOOK`, or `NOTIFY_SMTP_*` in `.env`. Console always prints.

---

## 4. Run the dashboard (buttons, no CLI needed)

```powershell
.\.venv\Scripts\python.exe -m streamlit run dashboard/app.py
```

Open http://localhost:8501 (or the printed Local URL). Six tabs:

| Tab | What it does |
|-----|--------------|
| **Contrôle** | Run each agent with a button (source / countries / date / limit inputs) + notifications check |
| **Tender Feed** | Searchable/filterable tender reports, per-row save to favorites |
| **Partenaires** | Partner directory with filters, save to favorites |
| **Événements & Leads** | Event calendar + prioritized leads, filters, save |
| **Favoris** | Bookmarked tenders/partners/leads, remove buttons |
| **Assist** | Chat with Faveod Assist (ask, search, run agents, save favorites) |

The data shown updates instantly after a button run (files are rewritten by
`control/runner.py`).

## 5. Run the chat agent

```powershell
# One-shot question
.\.venv\Scripts\python.exe -m chat "Combien de partenaires qualifiés avons-nous ?"

# Interactive chat loop
.\.venv\Scripts\python.exe -m chat --interactive

# Show tool-call logs while debugging
.\.venv\Scripts\python.exe -m chat "cherche les appels d'offres récents au Maroc" --verbose
```

Works in French, English and Arabic. Example prompts to try:

- "Résume l'état des agents"  (calls `dashboard_summary`)
- "Cherche les tenders récents au Maroc"  (calls `search_tenders` with date filter)
- "Quels partenaires qualifiés avons-nous ?"  (calls `search_partners`)
- "Lance le scanner des appels d'offres"  (calls `run_tender_hunter`)
- "Enregistre le lead LH-0001 dans les favoris"  (calls `save_item`)

> If the LLM is rate-limited or has no key, the chat still answers using a
> local fallback (same intents, answered from the stored data).

---

## 6. Everything in Docker

```powershell
# Qdrant + SearXNG + all three agents + dashboard
docker compose --profile app up
```

---

## 7. Automated tests

All suites are **pytest-free**: run them directly, one per agent/feature.

```powershell
.\.venv\Scripts\python.exe tests\test_guardrails.py      # Agent 1  (6 tests)
.\.venv\Scripts\python.exe tests\test_partner_scout.py   # Agent 2  (8 tests)
.\.venv\Scripts\python.exe tests\test_event_mapper.py    # Agent 3  (7 tests)
.\.venv\Scripts\python.exe tests\test_multilingual.py    # Phase 5  (6 tests, FR/EN/AR)
.\.venv\Scripts\python.exe tests\test_control.py         # Phase 6  (4 tests, date filters + favorites)
.\.venv\Scripts\python.exe tests\test_chat.py            # Phase 6  (5 tests, tool loop + fallback)
```

Run them all in one go:

```powershell
Get-ChildItem tests\test_*.py | ForEach-Object { python $_.FullName }
```

Expected output: each suite prints `ok <test_name>` lines and ends with
`ALL ... TESTS PASSED`.

### What each suite verifies

| Suite | What it proves |
|-------|----------------|
| `test_guardrails.py` | Similarity gate (below 0.75 the LLM is not consulted); verbatim evidence verification; hallucinated quotes dropped; invalid statuses; LLM-unavailable honesty; fit score formula |
| `test_partner_scout.py` | Custom-dev partners kept; SAP/Oracle/low-code resellers disqualified; no-pages manual review; affinity score weights; profiler evidence guardrails; offline end-to-end pipeline |
| `test_event_mapper.py` | Role classification (CIO/CISO/Minister/IT Director = decision-makers); NER evidence guardrail; content-too-thin; LLM-unavailable; lead score & priority weights; offline pipeline + graph fan-out |
| `test_multilingual.py` | Real French PDF, English PDF and Arabic DOCX parsing; guardrails hold in every language; fit score honesty |
| `test_control.py` | Date filters (`RECENT_DAYS`, `UPCOMING_DAYS`) and the saved-items store (save/remove/dedupe) |
| `test_chat.py` | Tool-calling loop (tool → result → answer), bad-argument handling, LLM-unavailable local fallback, intent matching, message rendering |

---

## 8. Manual verification checklist (after a run)

1. **Agents produce output** - after a sample run each of these exists and is
   non-empty:
   - `data/output/latest.json` (reports)
   - `data/output/partners_latest.json` / `qualified_partners.json`
   - `data/output/leads_latest.json` / `priority_leads.json`
2. **Date filter** - `python -m tender_hunter run --sources sample --days 10`
   prints `recent filter: N -> M ...`; expect M < N.
3. **Dashboard** - every tab renders without a red error box; clicking a run
   button in Contrôle shows a JSON result and refreshes the feed tabs.
4. **Favorites** - save a tender from Tender Feed, it appears in Favoris, and
   the "Retirer" button removes it.
5. **Chat** - ask a summary question, a filtered search, a "run agent" request,
   and a "save favorite" request; verify the answers cite real IDs/numbers from
   the data and that `data/saved.json` changes.
6. **Notifications** - `python -m notifications check --dry-run` prints the
   alert digest; running twice does not re-alert the same items (dedup).

---

## 9. Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| Console shows `no LLM API key configured` | Reasoning runs in guardrail-only (manual review) mode. Expected without `OPENROUTER_API_KEY`. |
| LLM calls fail with 429 | OpenRouter free-tier daily quota exhausted; the chat falls back to local answers automatically. Retry the next day. |
| Embedding calls fail with 429 | Gemini free-tier RPM throttle; the embedder retries with backoff automatically. |
| Live sources return nothing (AfDB/IMF 403/404) | Adapters are ready; the network is blocking them. Sample data is seeded automatically so pipelines still run. |
| SPA websites give thin text | Add a Playwright renderer (planned, see `PHASE6_AGENTIC_UI_CHAT.md` §5). |
| Weird characters in chat CLI output on Windows | Console codepage; output is reconfigured to UTF-8 automatically. Use `chcp 65001` if needed. |

---

## 10. Where the outputs are

```
data/
├── output/
│   ├── reports.jsonl  latest.json  high_value.json      # Agent 1
│   ├── partners.jsonl  partners_latest.json  qualified_partners.json  # Agent 2
│   ├── events.jsonl  events_latest.json  leads.jsonl  leads_latest.json  priority_leads.json  # Agent 3
├── saved.json                                          # Favorites (Phase 6)
├── state/notified.json                                 # Notification dedup state
├── logs/*.log                                          # Per-agent logs
└── downloads/ sample_docs/                             # Documents
```
