# PHASE 6 — Agentic Control Center, AI Assistant & Full-Button UI — Implementation Notes

> What was built, how it works, and how to run it.
> Project: Faveod Sovereign Multi-Agent Intelligence System (Phase 6).

---

## 1. Overview

Phase 6 removes the last friction: **the client no longer executes CLI
commands**. Everything is driven from the dashboard with **buttons**, and the
new **chat agent** (`Faveod Assist`) can do all of it too — summarize the
agents' state, search with country/score/**date** filters, launch agents, and
bookmark favorites, in French, English or Arabic.

It also documents the **remaining blueprint integrations** that were missing
after the first five phases (sovereign model serving, Playwright for JS-heavy
portals, residential proxies, FR/EN prompt split, CRM push, interactive event
calendar, scheduled scans).

---

## 2. What was delivered

| Task | Status | Notes |
|------|--------|-------|
| 6.1 Button-Based Control Center (no CLI) | ✅ Done | `control/` runners call the three agents' graphs in-process; `data/saved.json` favorites store; Control Center tab runs each agent with source / country / date / limit inputs; result JSON shown after each run |
| 6.2 Faveod Assist — Chat Agent (client-facing) | ✅ Done | `chat/` tool-calling loop over the shared LLM client (tools: summary, search×3 with filters, run×3, save_item, help); LLM-free local fallback; dashboard **Assist** tab + `python -m chat` CLI |
| 6.3 Date Filters for Search | ✅ Done | `RECENT_DAYS` (tenders: published/deadline ≤ N days) and `UPCOMING_DAYS` (events: start within next N days) wired into config, CLIs (`--days`), registries, dashboard filters and chat search tools |
| Missing blueprint integrations | 📋 Documented | see §5 — checklist of what is still to build |

---

## 3. Project layout (new in Phase 6)

```
control/                     # TASK 6.1 — programmatic agent runs + favorites
├── runner.py                #   run_tenders / run_partners / run_events (in-process,
│                            #   writes the same data/output/ files as the CLIs)
└── saved.py                 #   saved.json store (tenders / partners / leads)

chat/                        # TASK 6.2 — Faveod Assist
├── assistant.py             #   ChatAssistant: LLM tool-calling loop + history
├── tools.py                 #   TOOLS registry (search/run/save) with date filters
├── prompts.py               #   system prompt + transcript builder
├── fallback.py              #   local pattern-based answers (LLM unavailable)
└── __main__.py              #   python -m chat "question" / --interactive

dashboard/app.py             # Phase 6 UI: 6 tabs — Contrôle / Tender Feed /
                             #   Partenaires / Événements & Leads / Favoris / Assist
```

### 3.1 How the Control Center works

`control/runner.py` mirrors the CLI `_run_once` flow but as plain functions:

```python
from control import runner
runner.run_tenders(sources=["sample"], recent_days=10, limit=0)
runner.run_partners(source="sample", countries=["Morocco"], limit=0)
runner.run_events(source="sample", upcoming_days=30, limit=0)
```

Each sets the relevant config, builds the agent's LangGraph components,
`run_once`s the graph, and writes the standard output files — so the dashboard
tabs update immediately after a click. Because the agents degrade gracefully
(no API key → guardrail-only mode), the buttons always produce a result.

Favorites are stored in `data/saved.json`; every feed row can be bookmarked
(`➕ Enregistrer`) and unbookmarked (`🗑 Retirer`) from the **Favoris** tab.

### 3.2 How the chat agent works

`ChatAssistant.answer(message)` runs a loop (max 5 steps):

1. The LLM receives the system prompt (tool catalogue + JSON-only rules) and the
   recent transcript.
2. If it returns `{"tool": "<name>", "arguments": {...}}`, the tool executes
   (`chat/tools.py`), the JSON result is appended to the history, loop again.
3. If it returns `{"answer": "..."}`, that text is returned to the user.
4. If the LLM is unavailable (no key, quota exhausted, 429) or returns
   unparseable output, `chat/fallback.py` answers locally from the stored data.

The chat can therefore run agents and save favorites exactly like the buttons
do — the tools share the same `control.runner` and `control.saved` modules.

### 3.3 Date filters

- **Tenders (`RECENT_DAYS`, default 0)** — `tender_hunter/ingest/registry.py`
  keeps only tenders whose `publication_date` (fallback `deadline`) falls within
  the last N days; tenders without a parseable date are dropped while the filter
  is active.
- **Events (`UPCOMING_DAYS`, default 0)** — `event_mapper/ingest/registry.py`
  keeps only events starting within the next N days.
- Exposed as `--days` on both CLIs, as number inputs in the dashboard filters
  and Control Center, and as `recent_days` / `upcoming_days` arguments on the
  chat search/run tools.

---

## 4. How to run

```powershell
# Dashboard with full control (open http://localhost:8501)
.\.venv\Scripts\python.exe -m streamlit run dashboard/app.py

# Chat agent
.\.venv\Scripts\python.exe -m chat "Combien de partenaires qualifiés avons-nous ?"
.\.venv\Scripts\python.exe -m chat --interactive

# Date-filtered CLIs
.\.venv\Scripts\python.exe -m tender_hunter run --sources sample --days 10
.\.venv\Scripts\python.exe -m event_mapper run --source sample --days 30

# Phase 6 tests
.\.venv\Scripts\python.exe tests\test_control.py
.\.venv\Scripts\python.exe tests\test_chat.py
```

---

## 5. Missing blueprint integrations (next)

These items from the original plan are still open; each is ready for its own
phase:

| # | Integration | Why / How |
|---|-------------|-----------|
| 6.4 | **Sovereign model serving** (Deployment 1) | Run `vLLM`/`Ollama` locally with `Qwen-2.5`, `DeepSeek-R1-Distill`, `BGE-M3`; the client already supports this — set `LLM_BASE_URL` to the local endpoint and `EMBEDDING_PROVIDER=local`. |
| 6.5 | **Playwright/Puppeteer rendering** | Live tender/event portals serve HTML via JS; add a headless renderer in `tender_hunter/ingest` and `event_mapper/ingest` for thin-text pages. |
| 6.6 | **Residential proxy rotation** | Replace the free `PROXY_LIST` with a rotating residential pool for geo-blocked portals (AfDB, IMF currently 403/404). |
| 6.7 | **Reasoning in EN, output in FR/AR** | Keep chain-of-thought in English; emit French/Arabic field labels + summaries in the JSON output. |
| 6.8 | **CRM push** | HubSpot/Salesforce connector for qualified partners + priority leads (a `crm/` package mirroring `notifications/`). |
| 6.9 | **Interactive event calendar** | Month-grid calendar view in the dashboard with drill-down to per-event leads. |
| 6.10 | **Scheduled auto-scans** | Background scheduler so the Control Center runs agents on an interval without the CLI `--interval` flag. |

These are tracked in `tasks.md` under **Phase 6**.
