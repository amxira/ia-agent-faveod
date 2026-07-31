# PHASE 5 — Dashboard & Notifications — Implementation Notes

> What was built, how it works, and how to run it.
> Project: Faveod Sovereign Multi-Agent Intelligence System (Phase 5).

---

## 1. Overview

Phase 5 ties the three agents together:

- a **Streamlit dashboard** (`dashboard/`) that displays the Tender Feed, the
  Qualified-Partner Directory, and the IT Event Calendar with prioritized
  prospect lists;
- a **notification engine** (`notifications/`) that alerts the team (Slack,
  Teams, or email digest) the moment a high-value tender (≥ 80%) or a
  high-priority lead appears — with dedup so a run only alerts on *new* items;
- an **end-to-end multilingual validation** suite proving Agent 1 behaves
  correctly on real French, English and Arabic tender documents and that the
  anti-hallucination rules hold in every language.

Everything is sovereign: it runs locally or in Docker, reads the same
`data/output/` files the agents write, and needs no cloud dashboard service.

---

## 2. What was delivered

| Task | Status | Notes |
|------|--------|-------|
| 5.1 Dashboard & Notification Workflow | ✅ Done | Streamlit dashboard (3 tabs, reads agents' latest outputs) + notification engine (console / Slack / Teams / SMTP) with state-file dedup + scheduled mode |
| 5.2 End-to-End Validation & Multilingual Testing | ✅ Done | `tests/test_multilingual.py` runs Agent 1 against real FR (PDF), EN (PDF), AR (DOCX) sample tenders and asserts the guardrails hold in each language; one scoring honesty bug found & fixed |

---

## 3. Project layout

```
dashboard/                   # TASK 5.1 — Streamlit UI
├── data.py                  #   loads the agents' latest output files (Streamlit-free, testable)
└── app.py                   #   `streamlit run dashboard/app.py`

notifications/               # TASK 5.1 — alert engine
├── config.py                #   NOTIFY_* settings (Slack/Teams/SMTP thresholds)
├── notifier.py              #   detection (dedup via data/state/notified.json) + dispatch
└── __main__.py              #   `python -m notifications check [--dry-run|--reset|--interval N]`

tests/test_multilingual.py   # TASK 5.2 — 6 tests: FR/EN/AR parsing + guardrails
```

---

## 4. Dashboard (Task 5.1)

`dashboard/data.py` reads the same JSON the agents write, so no database or API
is needed:

| Tab | Reads | Shows |
|-----|-------|-------|
| **Tender Feed** | `latest.json` | count / high-value (≥80%) / average score metrics, sortable table, per-tender criteria statuses with similarity scores and verbatim citations |
| **Partner Directory** | `partners_latest.json` (+ `qualified_partners.json`) | scanned vs qualified metrics, table (tech focus, affinity, grade, contact), qualified-partner details with references |
| **Events & Leads** | `events_latest.json`, `leads_latest.json` | event calendar, prospect table with priority filter, per-lead key challenges & panel topics |

Run it, open http://localhost:8501:

```
python -m streamlit run dashboard/app.py
```

---

## 5. Notifications (Task 5.1)

`python -m notifications check`:

1. Reads the agents' latest outputs.
2. Flags **new** items only — `data/state/notified.json` remembers ids already
   alerted, so re-running never spams.
   - Tenders with `fit_score >= TENDER_ALERT_THRESHOLD` (default **80**).
   - Leads matching `LEAD_PRIORITY_FILTER` (default **HIGH PRIORITY**).
3. Formats a human-readable summary and dispatches to every configured channel:
   **console** (always), **Slack** webhook, **Teams** webhook, **SMTP** email.
   Channel failures are logged, never fatal.

Options: `--threshold N`, `--dry-run` (print only), `--reset` (forget seen
items), `--interval N` (scheduled loop). Docker profile `notify` runs one check
per container start.

---

## 6. Multilingual validation & anti-hallucination (Task 5.2)

`tests/test_multilingual.py` uses the **real** sample documents:

| Language | Document | Type |
|----------|----------|------|
| French | `tn-2026-001.pdf` (portail citoyen, France) | PDF |
| English | `tn-2026-002.pdf` (e-gov portal, Egypt) | PDF |
| Arabic | `tn-2026-005.docx` (RFP, UAE) | DOCX |

It verifies:
1. **Parsing** — each document yields non-trivial text (Arabic checked for
   Arabic script).
2. **Evidence guardrail in every language** — an LLM returning fabricated
   quotes is suppressed to `Unspecified - Manual review required` with
   `guardrail=evidence_not_found` and zero citations.
3. **LLM-unavailable in every language** — all criteria stay `llm_unavailable`,
   nothing guessed.
4. **Fit-score honesty** — a guardrail-held criterion forces
   `requires_manual_review=True` and a `(REVIEW)` grade.

**Bug found & fixed during validation:** `compute_fit_score` returned `POOR FIT`
without the `(REVIEW)` prefix when *all* criteria were guardrail-held
(`tender_hunter/reasoning/scoring.py`) — grade now honestly reads
`(REVIEW) POOR FIT`.

**Prompt parameters** remain at production-fine-tuned values: temperature 0.1,
`LLM_TIMEOUT=90`, `MAX_LLM_RETRIES=2`, `SIMILARITY_THRESHOLD=0.75` (all in
`tender_hunter/config.py`).

---

## 7. How to run

```powershell
# Dashboard
python -m streamlit run dashboard/app.py           # http://localhost:8501

# Notifications
python -m notifications check                      # dispatch new alerts
python -m notifications check --dry-run            # print only
python -m notifications check --reset              # re-alert after reset
python -m notifications check --interval 60        # scheduled

# Multilingual / end-to-end validation
python tests\test_multilingual.py                  # ALL MULTILINGUAL VALIDATION TESTS PASSED

# Full test sweep (all agents)
python tests\test_guardrails.py
python tests\test_partner_scout.py
python tests\test_event_mapper.py
python tests\test_multilingual.py
```

### Docker

```powershell
docker compose --profile app up                    # agents + dashboard (port 8501)
docker compose run --rm notifications              # one-shot alert check
```

---

## 8. Verified end-to-end

- ✅ Dashboard boots and serves the three tabs against the current
  `data/output/` (97 tenders, 8 partners / 4 qualified, 4 events, 12 leads).
- ✅ `python -m notifications check --dry-run` → 9 new alerts (2 high-value
  tenders + 7 high-priority leads); second run → 0 (dedup works); `--reset`
  → 9 again.
- ✅ Streamlit server verified headless on `:8599`.
- ✅ 6/6 multilingual validation tests pass; guardrails verified on real
  FR/EN/AR documents; scoring-honesty bug fixed.
- ✅ No regression in Agents 1–3 suites (6 + 8 + 7 tests).

---

## 9. Known limitations & next steps

- **Dashboard refresh** is manual (Streamlit `st.rerun`/browser reload); a
  scheduled agent loop (`--interval`) feeding the JSON is the intended cadence.
- **Notification delivery** is one-shot per new item; retries/backoff are left
  to the webhook provider. Email uses STARTTLS (port 587).
- **Fine-tuning prompts** was done at the parameter level (temperature etc.);
  deeper per-agent prompt tuning belongs with real production documents.
- **Next:** run the three agents on schedule, point the webhooks at the team's
  Slack/Teams channel, and consider deploying the dashboard behind a lightweight
  auth reverse-proxy if exposed outside the LAN.
