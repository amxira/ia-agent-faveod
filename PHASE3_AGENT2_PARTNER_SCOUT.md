# PHASE 3 — Agent 2 "Partner Scout" — Implementation Notes

> What was built, how it works, and how to run it.
> Project: Faveod Sovereign Multi-Agent Intelligence System (Phase 3 / Agent 2).

---

## 1. Overview

**Partner Scout** is the second agent of the Faveod intelligence system. It
automatically **discovers, analyzes, and qualifies** local IT services companies
(ESNs / systems integrators) in Faveod's target markets (Morocco, Senegal,
Tunisia, Egypt, Saudi Arabia, UAE) to act as local implementation or support
partners, and outputs a structured **Faveod Affinity Score (0–100%)** with a
partner directory.

It is built on the same foundation as Agent 1 (LangGraph, shared LLM client and
proxy middleware) and runs **fully offline with zero cost in development**, then
lights up live discovery through a **self-hosted SearXNG** instance and real
scoring via a free reasoning model.

---

## 2. What was delivered

| Task | Status | Notes |
|------|--------|-------|
| 3.1 Data Collection & Search Setup | ✅ Done | self-hosted SearXNG backend (JSON API), automated per-country × per-term queries, offline sample corpus, backend registry |
| 3.2 ESN Website & Portfolio Analyzer | ✅ Done | website fetcher (Case Studies / References / Partners discovery), LLM profiler with verbatim-evidence guardrails (custom dev vs low-code/SAP/Oracle resellers, references, scale, languages, contact) |
| 3.3 Partner Qualification & Database Engine | ✅ Done | deterministic competitor filter + weighted Faveod Affinity Score + structured partner output (JSONL / latest / qualified) |

---

## 3. Project layout

```
partner_scout/
├── config.py            # all settings, read from .env / environment (reuses Agent 1 infra)
├── models.py            # Pydantic models: ESNCompany, PageText, ESNProfile, QualifiedPartner
├── state.py             # LangGraph state schemas
├── graph.py             # LangGraph graph: search → parallel Send fan-out per company
├── pipeline.py          # per-company orchestration (scrape → analyze → qualify)
├── cli.py               # command-line interface
├── search/              # TASK 3.1
│   ├── base.py          #   SearchEngine base class (best-effort)
│   ├── searxng.py       #   self-hosted SearXNG JSON-API backend
│   ├── sample_data.py   #   8 offline companies with website corpora (zero network)
│   └── registry.py      #   backend registry + resilient search + sample fallback
├── scrape/              # TASK 3.2
│   ├── fetcher.py       #   homepage fetch + Case-Studies/References/Partners discovery
│   └── extract.py       #   boilerplate-stripping HTML→text + page classification
├── analyze/             # TASK 3.2
│   ├── prompts.py       #   company-profiler system prompt
│   └── analyzer.py      #   LLM profiling + verbatim-evidence guardrails
├── qualify/             # TASK 3.3
│   └── engine.py        #   competitor filter + Faveod Affinity Score formula
├── output/
│   └── writer.py        #   TASK 3.3 — writes partners.jsonl + latest + qualified
└── tests/test_partner_scout.py   # 8/8 passing qualification & guardrail tests
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
       └── [search]  →  discover companies (SearXNG queries, or sample corpus)
            │
            └── Send (one parallel branch per company)     ← LangGraph parallelism
                 └── [process_company] for each company:
                      1. fetch website pages            (home + case-studies/references/partners)
                      2. extract clean text per page    (bs4, boilerplate stripped)
                      3. LLM profile with guardrails    (free model via OpenRouter)
                           - every claim must quote the site verbatim
                           - unverifiable claims → "Unspecified - Manual review required"
                      4. deterministic qualification    (resellers excluded)
                      5. compute Faveod Affinity Score + grade
                      6. emit QualifiedPartner
            │
            └── partners accumulate → written to data/output/
```

---

## 5. Qualification & the Faveod Affinity Score (Task 3.3)

### Competitor filter (deterministic, before scoring)
Companies whose verified `tech_focus` is `low_code_reseller` or
`proprietary_reseller` (only reselling SAP / Oracle / low-code products, no
custom development) are **disqualified as direct competitors** — regardless of
how many references they have.

### Faveod Affinity Score weights (sum 1.0)

| Component | Weight | Meaning |
|-----------|--------|---------|
| Custom development capability | 0.30 | custom_development=1.0, mixed=0.6, resellers=0 |
| Local presence (country match) | 0.25 | confirmed country in target markets |
| References & scale | 0.20 | named clients + public-sector/enterprise scale |
| Web presence | 0.15 | analyzable pages + contact URL + website |
| Language coverage | 0.10 | FR/EN/AR coverage of Faveod's markets |

Grades: `>=70 STRONG PARTNER FIT`, `>=55 POSSIBLE PARTNER`, `>=40 WEAK PARTNER`,
else `POOR PARTNER FIT`; prefix `(REVIEW)` when manual review is required.
Companies scoring `>= AFFINITY_THRESHOLD` (60) and not disqualified land in
`qualified_partners.json`.

### Anti-hallucination guardrails (strict, tested)

1. **Content gate** — if no pages were fetched, or the extracted text is thinner
   than `MIN_PAGE_TEXT_CHARS`, the LLM is never called and the profile is flagged
   for manual review.
2. **Verbatim evidence check** — every quote the model returns must match the
   fetched page text word-for-word (normalized). Non-matching quotes are dropped.
3. **No evidence → no claim** — a field (tech focus, references, scale, languages,
   contact) is only populated if its evidence verified. Otherwise it is reported
   `Unspecified - Manual review required`.
4. **LLM unavailable** — no key or API failure → profile stays in guardrail-only
   mode. The engine never guesses.

**Result:** a thin or vague website, a reseller's marketing page, or a model
failure never produces a fabricated partner profile — it is honestly flagged.

---

## 6. Search sources: what works live vs. fallback

| Backend | Dev status | Notes |
|---------|-----------|-------|
| **SearXNG** | ✅ Live | self-hosted meta-search (`SEARXNG_URL`); JSON API must be enabled (provided in `docker/searxng/settings.yml`) |
| **Sample** | ✅ Offline | 8 built-in companies with website corpora (custom dev, mixed, resellers, thin sites) so the full pipeline runs with zero network |

Rotating **residential proxy** is reused from Agent 1: list free proxies in
`.env` (`PROXY_LIST`); a paid provider can be swapped in later without touching
the code.

---

## 7. Key decisions (consistent with Phase 2)

- **Analysis LLM:** reuse the OpenRouter client + free-model auto-discovery
  (`nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` by default). The system
  prompt is reasoning-model ready, so swapping in a *local* **Qwen-2.5** or
  DeepSeek-R1-Distill via vLLM/Ollama is a config change (`LLM_BASE_URL`,
  `LLM_MODEL`) — matching the sovereignty goal of tasks.md.
- **Qualification is deterministic:** the LLM extracts facts; the rules engine
  decides `qualified` / `disqualification_reason`. No LLM in the decision path.
- **No embeddings needed:** unlike tenders, partner pages are analyzed directly
  with a lexical verbatim check — cheaper and fully offline-compatible.
- **Search cost:** zero — self-hosted SearXNG + offline sample corpus.

---

## 8. How to run

### 8.1 Offline demo (works right now, no keys)
```
.venv\Scripts\python.exe -m partner_scout run --source sample
```

### 8.2 Live discovery (self-hosted SearXNG)
```
docker compose up searxng
.venv\Scripts\python.exe -m partner_scout run --source searxng
```

### 8.3 Scoped runs
```
.venv\Scripts\python.exe -m partner_scout run --countries Morocco Senegal Egypt --limit 12
.venv\Scripts\python.exe -m partner_scout sources
```

### 8.4 Scheduled monitoring
```
.venv\Scripts\python.exe -m partner_scout run --source searxng --interval 60
```
(one scan every 60 minutes; `--limit N` caps the number of partners).

### 8.5 With Docker
```
docker compose --profile app up      # SearXNG + partner-scout + tender-hunter + Qdrant
```

### 8.6 Tests
```
.venv\Scripts\python.exe tests\test_partner_scout.py
```
Result: `ALL PARTNER SCOUT TESTS PASSED` (8 tests: qualification rules, reseller
disqualification, mixed-score reduction, no-pages honesty, affinity weights,
evidence guardrail, LLM-unavailable fallback, offline pipeline run).

---

## 9. Output format (Task 3.3)

Partners are written to:

| File | Contents |
|------|----------|
| `data/output/partners.jsonl` | append-only history of every company |
| `data/output/partners_latest.json` | latest run, sorted by Affinity Score |
| `data/output/qualified_partners.json` | only companies ≥ `AFFINITY_THRESHOLD` and not disqualified |

Each partner contains:

```json
{
  "partner_id": "PS-MA-001",
  "company_name": "Atlas Custom Software",
  "country": "Morocco",
  "website": "https://www.atlascustom.example",
  "contact_url": "contact@atlas…",
  "size": "120 ingénieurs",
  "project_scale": "public_sector",
  "services": ["Développement sur mesure", "Intégration API"],
  "client_references": ["Ministère de l'Intérieur", "Banque Centrale du Maroc"],
  "languages": ["fr", "en"],
  "tech_focus": "custom_development",
  "affinity_score": 95.5,
  "affinity_grade": "STRONG PARTNER FIT",
  "qualified": true,
  "disqualification_reason": "",
  "requires_manual_review": false,
  "pages_analyzed": 2,
  "profile": {
    "evidence": ["…verbatim quote from the site…"],
    "citations": [{"document": "https://…/case-studies", "snippet": "…"}]
  }
}
```

---

## 10. What's tested / verified end-to-end

- ✅ `python -m partner_scout run --source sample` — 8 companies profiled and
  qualified through the full LangGraph graph (parallel branches).
- ✅ Real free-tier LLM verification — sane outcomes:
  | Company | Tech focus | Affinity | Verdict |
  |---------|-----------|----------|---------|
  | Atlas Custom Software (MA) | custom_development | 95.5% | STRONG, qualified |
  | Nile Digital (EG) | custom_development | 95.5% | STRONG, qualified |
  | Sahel Systems (SN) | mixed | 83.5% | STRONG, qualified |
  | Integra MENA (AE) | mixed | 63.5% | POSSIBLE, qualified (review) |
  | Maghreb Soft (TN, SAP reseller) | proprietary_reseller | 41.5% | DISQUALIFIED |
  | GulfSoft Solutions (AE, Oracle/PP) | low_code_reseller | 35.5% | DISQUALIFIED |
  | VisionTech Co (SA, thin site) | unspecified | 35.5% | manual review |
  | Delta Consulting (EG, vague) | unspecified | 35.5% | manual review |
- ✅ 4 partners written to `qualified_partners.json`; verified citations kept in
  each profile (e.g. 11 verbatim quotes for Atlas).
- ✅ Qualification & guardrail logic — 8/8 unit tests pass.
- ✅ All `partner_scout` modules compile cleanly.
- ✅ Agent 1's 6 guardrail tests still pass (no regression).

---

## 11. Known limitations & next steps

- **SearXNG quality** depends on the engines enabled in the instance settings;
  candidate discovery is only as good as the meta-search engines configured.
- **JS-rendered (SPA) websites** may yield thin text; a Playwright-based renderer
  can be added to `scrape/fetcher.py` later without touching the rest.
- **Duplicates / affiliate sites:** dedup is by root domain only; a post-pass
  merging same-company duplicates (by name similarity) is a good follow-up before
  Phase 5 displays the directory.
- **Contact enrichment** is best-effort (contact URL / mailto) and kept empty
  when unverifiable; LinkedIn/email enrichment is a natural Phase-4/5 extension.
- **Recommended next phases:** Phase 4 (Event Mapper & Lead Profiler), Phase 5
  (dashboard merging the tender feed + partner directory + alerts when a tender
  ≥ 80% is detected).
