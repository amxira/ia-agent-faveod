# PHASE 2 — Agent 1 "Tender Hunter" — Implementation Notes

> What was built, how it works, and how to run it.
> Project: Faveod Sovereign Multi-Agent Intelligence System (Phase 2 / Agent 1).

---

## 1. Overview

**Tender Hunter** is the first agent of the Faveod intelligence system. It
automatically **finds, downloads, parses, and scores** international software
tenders (World Bank, AfDB, EBRD, IMF) against Faveod's 4 mandatory criteria,
and outputs a structured **Faveod Fit Score (0–100%)** with exact document
citations.

It is built on **LangGraph** (installed for the project) and is designed to run
**fully offline with zero cost in development**, then light up real scoring
when you add two free API keys.

---

## 2. What was delivered

| Task | Status | Notes |
|------|--------|-------|
| 2.1 Data Ingestion & Scraping Engine | ✅ Done | Live scrapers for WB + EBRD; adapters for AfDB/IMF; proxy middleware; offline sample dataset |
| 2.2 Document Parsing & RAG Pipeline | ✅ Done | PyMuPDF + python-docx extraction, page-aware chunking, Qdrant vector store, Gemini embeddings (BGE-M3 swap-in ready) |
| 2.3 Reasoning Engine (Faveod Criteria Filter) | ✅ Done | DeepSeek-R1 prompt for the 4 criteria + 3 anti-hallucination guardrails |
| 2.4 Agent Output Generation | ✅ Done | JSON reports with Fit Score, grades, page-level citations |

---

## 3. Project layout

```
tender_hunter/
├── config.py            # all settings, read from .env / environment
├── models.py            # Pydantic models: Tender, CriterionResult, FaveodReport, Citation
├── state.py             # LangGraph state schemas
├── graph.py             # LangGraph graph: scrape → parallel Send fan-out per tender
├── pipeline.py          # per-tender orchestration (parse → embed → index → score)
├── cli.py               # command-line interface
├── ingest/              # TASK 2.1
│   ├── base.py          #   TenderSource base class + HTTP helper
│   ├── proxy.py         #   rotating proxy middleware (free pool, direct fallback)
│   ├── world_bank.py    #   World Bank live API
│   ├── ebrd.py          #   EBRD live notices (ECEPP portal)
│   ├── afdb.py          #   AfDB adapter (blocked from dev network, graceful)
│   ├── imf.py           #   IMF adapter (blocked from dev network, graceful)
│   ├── sample_data.py   #   offline multilingual sample dataset generator
│   └── registry.py      #   source registry + resilient fetch
├── parse/               # TASK 2.2
│   ├── documents.py     #   PDF (PyMuPDF) / DOCX (python-docx) / HTML / TXT extraction
│   └── chunker.py       #   page-aware text chunking with overlap
├── embedding/           # TASK 2.2
│   ├── base.py          #   Embedder interface + cosine helpers
│   ├── gemini.py        #   Google Gemini embeddings (free tier, REST, no SDK)
│   └── local.py         #   zero-dependency hashing fallback (offline mode)
├── vectorstore/         # TASK 2.2
│   └── store.py         #   Qdrant (server or in-memory), cosine distance
├── reasoning/           # TASK 2.3
│   ├── prompts.py       #   DeepSeek-R1 system prompt + 4 criteria definitions
│   ├── engine.py        #   guardrail-driven evaluation engine
│   └── scoring.py       #   Faveod Fit Score formula + grades
├── llm/
│   └── client.py        #   OpenAI-compatible client → OpenRouter (DeepSeek-R1 free)
├── output/
│   └── report.py        #   TASK 2.4 — writes JSONL + latest.json + high_value.json
├── Dockerfile           # container image for the agent
├── docker-compose.yml   # Qdrant service + optional app service
├── .env.example         # copy to .env and add API keys
├── requirements.txt
└── tests/test_guardrails.py  # 6/6 passing guardrail & scoring tests
```

---

## 4. How the pipeline works

```
CLI run
  └── LangGraph StateGraph
       └── [scrape]  →  fetch tenders from configured sources (WB, EBRD, ...)
            │
            └── Send (one parallel branch per tender)     ← LangGraph parallelism
                 └── [process_tender] for each tender:
                      1. download / locate documents (PDF, DOCX)
                      2. extract text per page   (PyMuPDF / python-docx)
                      3. chunk text with overlap (page-aware)
                      4. embed chunks            (Gemini, or local fallback)
                      5. index into Qdrant       (in-memory if no server)
                      6. evaluate 4 criteria with guardrails  (DeepSeek-R1 via OpenRouter)
                      7. compute Fit Score + citations
                      8. emit FaveodReport
            │
            └── reports accumulate → written to data/output/
```

---

## 5. The 4 Faveod criteria (Task 2.3)

1. **Source Code / IP Ownership** — does the client retain 100% IP rights? (weight 35%)
2. **High Security / Quality** — local/sovereign hosting, ISO 27001, RGPD/NIS-2, audits? (30%)
3. **Compressed Timelines** — tight, penalty-enforced deadlines? (20%)
4. **Green-IT** — digital sobriety / eco-design requirements? (15%)

### Anti-hallucination guardrails (strict, tested)

1. **Similarity gate** — each criterion question is embedded and compared to the
   tender's chunks. If the best similarity is below **0.75**, the question is
   **never sent to the LLM** and the output is
   `"Unspecified - Manual review required"`.
2. **Verbatim evidence check** — every quote the model returns must match the
   retrieved text word-for-word. Non-matching quotes are dropped.
3. **No evidence → no verdict** — if no quote verifies, the verdict is suppressed
   and the criterion is marked for manual review (prevents hallucinated
   clauses/pages).
4. **Valid status only** — anything other than `SATISFIED` / `PARTIAL` /
   `NOT_SATISFIED` is rejected.

**Result:** in offline/dev mode (no API keys) every criterion is honestly
flagged `[MANUAL REVIEW]` instead of guessing. This is the designed, safe
behaviour — and it is exactly what Task 5.2 asks to verify.

---

## 6. Sources: what works live vs. fallback

| Source | Dev status | Notes |
|--------|-----------|-------|
| **World Bank** | ✅ Live | free `search.worldbank.org` API; returns ICT/digital projects whose procurement produces tenders |
| **EBRD** | ✅ Live | scrapes the real ECEPP notice table (title, country, closing date, notice type) |
| **AfDB** | ⚠️ Blocked from your network (404/timeouts) | adapter is ready; works once reachable / with residential proxies |
| **IMF** | ⚠️ Blocked (403) | adapter is ready; same as above |
| **Sample** | ✅ Offline | generates French/Arabic/English tender PDFs + DOCX so the full pipeline runs with zero network |

Rotating **residential proxy** is implemented as an interface
(`ingest/proxy.py`): free proxies can be listed in `.env` (`PROXY_LIST`), and a
paid residential provider can be swapped in later without touching the rest of
the code.

---

## 7. Key decisions (per your answers)

- **Reasoning LLM:** OpenRouter, default model `deepseek/deepseek-r1:free`
  (configurable). Client is OpenAI-compatible, so vLLM/Ollama endpoints work too.
- **Embeddings:** Google Gemini free-tier API (`gemini-embedding-001`) via REST;
  automatic fallback to a local hashing embedder when no key is set, so RAG
  never hard-depends on a network call. BGE-M3 can replace it via the same
  `Embedder` interface.
- **Vector DB:** Qdrant. Connects to a running server when `QDRANT_URL` is set
  (see docker-compose), otherwise transparently runs in-memory — no Docker
  required to start developing.
- **Scraping cost:** zero — only free public endpoints + offline sample data.

---

## 8. How to run

### 8.1 Offline demo (works right now, no keys)
```
.venv\Scripts\python.exe -m tender_hunter run --sources sample
```

### 8.2 Full pipeline with live sources
```
.venv\Scripts\python.exe -m tender_hunter run --sources sample world_bank ebrd
```

### 8.3 Real scoring (add 2 free API keys)
1. Copy `.env.example` → `.env`
2. `OPENROUTER_API_KEY=...`  (free model `deepseek/deepseek-r1:free`)
3. `GEMINI_API_KEY=...`      (free tier embeddings)
4. Re-run any `run` command → criteria are now evaluated by DeepSeek-R1.

### 8.4 Scheduled monitoring
```
.venv\Scripts\python.exe -m tender_hunter run --sources sample world_bank ebrd --interval 60
```
(one scan every 60 minutes; `--limit N` caps the number of reports).

### 8.5 With Docker / Qdrant server
```
docker compose up qdrant                       # start the vector DB
docker compose --profile app up                # agent + qdrant
```

### 8.6 Tests
```
.venv\Scripts\python.exe tests\test_guardrails.py
```
Result: `ALL GUARDRAIL TESTS PASSED` (6 tests: similarity gate, verdict +
citation, hallucinated evidence, invalid status, unavailable LLM, fit score).

---

## 9. Output format (Task 2.4)

Reports are written to:

| File | Contents |
|------|----------|
| `data/output/reports.jsonl` | append-only history of every report |
| `data/output/latest.json`   | latest run, sorted by Fit Score |
| `data/output/high_value.json` | tenders scoring ≥ 80% (alert candidates) |

Each report contains:

```json
{
  "tender_id": "TN-2026-001",
  "source": "sample",
  "title": "Développement d'une plateforme de services numériques (portail citoyen)",
  "fit_score": 87.5,
  "fit_grade": "STRONG FIT",
  "requires_manual_review": false,
  "criteria": [
    {
      "criterion": "ip_ownership",
      "label": "Source Code / IP Ownership",
      "status": "SATISFIED",
      "similarity_score": 0.91,
      "confidence": 0.95,
      "rationale": "…",
      "citations": [
        {
          "document": "tn-2026-001.pdf",
          "page": 2,
          "chunk_id": "…",
          "snippet": "Tout le code source … sera la propriété pleine et entière de l'Administration…"
        }
      ]
    }
  ]
}
```

Fit Score formula: weighted average of the criteria that could be verified
(SATISFIED = 1.0, PARTIAL = 0.5, NOT_SATISFIED = 0.0). Any criterion marked
`"Unspecified - Manual review required"` forces `requires_manual_review: true`
and prefixes the grade with `(REVIEW)` — no guesswork is ever hidden.

---

## 10. What's tested / verified end-to-end

- ✅ `python -m tender_hunter run --sources sample` — 5 multilingual tenders
  parsed (French PDF, English PDFs, Arabic DOCX), chunked, embedded, indexed,
  scored, exported to JSON.
- ✅ `--sources sample world_bank ebrd` — 97 tenders ingested in one run and
  processed through the full LangGraph graph (parallel branches).
- ✅ Live World Bank API verified (returns real project data).
- ✅ Live EBRD ECEPP scraping verified (50 real notices with countries & closing dates).
- ✅ Guardrail & scoring logic — 6/6 unit tests pass.
- ✅ All 36 Python files compile cleanly.

---

## 11. Known limitations & next steps

- **AfDB / IMF** return nothing from your current network (404/403). Fix: reachable
  network or residential proxies; the adapters need no code changes.
- **World Bank** yields *projects* (the free API has no direct tender-notice
  feed); notice-level data still needs a follow-up crawl of the project detail
  pages. A dedicated procurement-notices scraper can be added later.
- **Fit Score** is only meaningful once `OPENROUTER_API_KEY` + `GEMINI_API_KEY`
  are set; otherwise criteria are honestly held in manual-review mode.
- **Recommended next phases:** Phase 3 (Partner Scout), Phase 5 dashboard +
  alerts (Slack/Teams/email when a tender ≥ 80% is detected).
