# Faveod Intelligence — Frontend Specification

This document describes **everything the frontend must do**. It is the contract
between the Python backend (FastAPI, `api/`) and the future UI.

**Status: to be built.** The backend is already done and documented live by
Swagger at `http://localhost:8000/docs`. Build the frontend against that API.

---

## 1. Goal

A web application that replaces the old Streamlit dashboard. It lets Faveod's
International Business Development team:

1. **See** the agents' latest intelligence in one place — tenders, partners,
   events, leads.
2. **Drive** the three agents (run them, watch progress, read logs) without a
   terminal.
3. **Act** — bookmark results, review citations, and ask the built-in AI
   assistant (Faveod Assist) for summaries and targeted searches.

The UI is a **client** only. All data access and all agent runs go through the
REST API. There is no direct filesystem/DB access from the frontend.

---

## 2. Recommended stack

Nothing is enforced — these are sensible defaults for a self-hosted internal
tool:

| Layer | Suggestion | Why |
|-------|-----------|-----|
| Framework | **React + Vite** (or Next.js) | large ecosystem, quick iteration |
| Language | **TypeScript** | the API returns JSON; typed models prevent bugs |
| UI kit | **Mantine** or **Ant Design** | tables, forms, drawers, notifications out of the box |
| State | **TanStack Query** | caching + retry + background refetch for the API |
| Routing | **React Router** (or Next.js pages) | pages listed in §4 |
| Charts | **Recharts** (scores, calendars) | lightweight, React-friendly |
| HTTP | native `fetch` or **axios** | thin typed client generated from OpenAPI |

> Tip: FastAPI exposes the OpenAPI schema at `/openapi.json`. You can generate a
> typed client with `openapi-typescript` or `@hey-api/openapi-ts` so the whole
> API is auto-typed.

---

## 3. Backend API contract (what to build against)

Base URL: `http://localhost:8000`. Swagger: `http://localhost:8000/docs`.

### 3.1 System
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/health` | liveness check `{status:"ok"}` |
| GET | `/api/agents/options` | dropdown options: `tender_sources`, `partner_sources`, `event_sources`, `countries`, `kinds` |

### 3.2 Data (read)
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/summary` | counts for the overview cards |
| GET | `/api/tenders?query&country&min_score&recent_days&limit` | tender feed |
| GET | `/api/tenders/{tender_id}` | tender detail |
| GET | `/api/partners?query&country&qualified_only&min_score&limit` | partner directory |
| GET | `/api/partners/{partner_id}` | partner detail |
| GET | `/api/events?query&country&upcoming_days&limit` | event list (has `lead_count`) |
| GET | `/api/events/{event_id}` | event detail |
| GET | `/api/leads?query&country&min_score&priority&days&limit` | prospect list |
| GET | `/api/leads/{lead_id}` | lead detail |

### 3.3 Favorites
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/saved` | all bookmarks resolved with latest data |
| POST | `/api/saved/{kind}/{item_id}` | save (`kind`: `tenders` \| `partners` \| `leads`) |
| DELETE | `/api/saved/{kind}/{item_id}` | remove bookmark |

### 3.4 Actions (run agents — slow, blocking)
| Method | Path | Body |
|--------|------|------|
| POST | `/api/run/tenders` | `{sources?, recent_days?, limit?}` |
| POST | `/api/run/partners` | `{source?, countries?, limit?}` |
| POST | `/api/run/events` | `{source?, countries?, upcoming_days?, limit?}` |
| POST | `/api/notifications/check` | `{threshold?, dry_run?, reset?}` |

Each run returns a summary `{ok, <counts>, duration_s, sources/countries}` plus a
`log` string (last ~10k chars) the UI can show in an expandable "execution log".

### 3.5 Chat
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/chat` | body `{message, session_id?, max_steps?}` → `{session_id, reply, history}` |
| DELETE | `/api/chat/{session_id}` | forget a conversation |

`history` is a list of entries `{role: "user"\|"assistant"\|"tool", content, name?}`
where `name` is the executed tool name and `content` is its JSON result — the UI
should render tool calls as collapsible cards (like the old dashboard's "Outil
exécuté" expanders).

---

## 4. Pages

### 4.1 Overview (`/`)
Dashboard landing page.
- **Metric cards** from `/api/summary`:
  - Tenders analyzed, high-value (≥80%), average fit score, manual-review count
  - Partners scanned, qualified, "good fit" (≥70%)
  - Events tracked, leads profiled, high-priority leads
  - Saved counts per kind
- **Quick actions**: buttons linking to Control Center runs and to each feed.
- Optional **"last results"** preview lists (top 5 tenders, top partners, top
  leads) using the list endpoints with `limit=5`.

### 4.2 Control Center (`/control`)
Run agents with buttons (no CLI).
- Per agent a form:
  - **Tender Hunter**: multi-select sources, recent-days, limit.
  - **Partner Scout**: source, countries multi-select, limit.
  - **Event Mapper**: source, countries, upcoming-days, limit.
- **Notifications**: threshold slider + "check & notify" button.
- After a run: show the result summary JSON + expandable execution log
  (`result.log`). Disable the button while running (spinner + elapsed time).
- **Long-running UX**: agent runs can take minutes. Show a progress state;
  optionally poll a future job endpoint (§7) if implemented.

### 4.3 Tender Feed (`/tenders`)
- **Filters**: keyword search, country dropdown, min fit score (slider 0–100),
  recent-days window, plus "requires manual review" toggle.
- **Table**: tender id, title, country, deadline, fit score % (badge + grade),
  manual-review flag. Sortable by score/deadline. Paginated.
- **Row click → detail panel** (drawer or page):
  - Title, agency/source, country, deadline, URL, summary
  - Fit score + grade
  - **Per-criterion cards** (the 4 Faveod criteria): status, similarity score,
    rationale, **citations with verbatim quotes** — show them prominently, this
    is the anti-hallucination proof.
- **Save / unsave** button (toggled against `/api/saved/tenders/{id}`).

### 4.4 Partner Directory (`/partners`)
- **Filters**: keyword, country, qualified-only toggle, min affinity score.
- **Table**: company, country, tech focus, services, affinity %, grade,
  qualified badge, website link.
- **Detail panel**: profile (size, project scale, client references, languages,
  contact URL), rationale, **evidence/citations**, disqualification reason if
  any, pages analyzed.
- **Save / unsave**.

### 4.5 Events & Leads (`/events`)
Two views, one page:
- **Events list/calendar**: ranked by `lead_count` then start date. Optional
  month-grid calendar view (future enhancement, §6).
- **Leads table**: person, job title, company, country, event, score %, priority
  badge (HIGH/MEDIUM/LOW), decision-maker flag. Filters: priority, keyword,
  country, min score, recent days.
- **Lead detail**: person card (name, title, company, country), decision-maker
  status + reason, seniority, panel topics, key challenges, event link, evidence.
- **Save / unsave** for leads; events themselves are not bookmarkable.

### 4.6 Favorites (`/saved`)
- Three sections (tenders / partners / leads) listing bookmarked items with the
  same detail interaction as the feeds.
- One-click remove.

### 4.7 Assist — AI Chat (`/assist`)
- Chat bubbles: user / assistant; render `tool` history entries as collapsible
  cards with the JSON payload or a small table.
- **Multilingual**: the assistant replies in FR / EN / AR based on the user's
  message. The UI shell can be FR (current project language) with AR ready.
- Send `session_id` on every turn to keep context; offer a "new conversation"
  button (`DELETE /api/chat/{session_id}`).
- Input placeholder: "Posez votre question (FR / EN / AR)…"

### 4.8 Global shell
- Top navbar with the 7 links above + the API docs link (`/docs`).
- Loading skeletons per page; empty states with a hint to run an agent from the
  Control Center; error toasts when the API is unreachable.

---

## 5. Reusable components

| Component | Notes |
|-----------|-------|
| `ApiClient` | typed wrapper around `fetch`, base URL from env, JSON errors surfaced |
| `DataTable` | sorting, pagination, column config, loading/empty/error states |
| `ScoreBadge` | colored by value: red <60, amber 60–80, green ≥80 (tenders/partners/leads) |
| `PriorityBadge` | HIGH / MEDIUM / LOW colors |
| `ManualReviewChip` | flags items with `requires_manual_review` |
| `CitationBlock` | renders `criteria[].citations` with verbatim quotes + page refs |
| `FilterBar` | keyword, country, score, date-window controls used by the 3 feeds |
| `SaveButton` | heart/bookmark toggle calling POST/DELETE `/saved/{kind}/{id}` |
| `DetailDrawer` | slide-over showing the full record + citations |
| `RunAgentPanel` | form + run button + result summary + expandable log |
| `ChatBubble` / `ToolCard` | chat UI + collapsible tool-call cards |
| `EmptyState` / `ErrorState` / `LoadingSkeleton` | consistent feedback |

---

## 6. Definitions of done / acceptance criteria

The frontend is "done" when a user can, **without touching a terminal**:
- [ ] See live counts and top results on the Overview.
- [ ] Run all three agents with chosen options from the Control Center and read
      the execution log.
- [ ] Filter, sort, paginate and open details for tenders, partners, events and
      leads; see criteria + verbatim citations for tenders.
- [ ] Bookmark and unbookmark tenders / partners / leads; review them in
      Favorites.
- [ ] Ask Faveod Assist questions in FR / EN / AR, see the tool calls it makes,
      and start a fresh conversation.
- [ ] Run the notifications check and see which channels fired.
- [ ] The whole app degrades gracefully when the API is down (error states, no
      crashes).

---

## 7. Out of scope / future (documented so the UI can plan for it)

- **Job/task queue**: agent runs are currently synchronous (the HTTP call blocks
  until the run finishes). A later backend upgrade may add `POST /api/jobs` +
  `GET /api/jobs/{id}` polling; design the RunAgentPanel so the run-button
  handler is swappable to a job/poll flow.
- **Auth**: the API has none (self-hosted internal tool). If the frontend is
  exposed publicly later, a login layer + API keys will be added; keep the
  ApiClient auth-agnostic (header injection point).
- **Interactive event calendar**: month-grid with drill-down to leads (item from
  the blueprint backlog).
- **CRM push**: exporting qualified partners / priority leads to HubSpot /
  Salesforce will surface as read endpoints; the UI just needs export buttons.
- **Notifications history page**: a future endpoint may list past alerts.
- **PWA/offline**: not required; the API is the single source of truth.

---

## 8. Practical notes for the frontend developer

- Keep the base URL configurable (`VITE_API_BASE` / `NEXT_PUBLIC_API_BASE`),
  default `http://localhost:8000`.
- Scores come as floats already in `[0,100]`; grades are strings like
  `"(REVIEW) POOR FIT"` — render them as-is.
- IDs: tenders use `tender_id`, partners `partner_id`, leads `lead_id`, events
  `id`. Use those exact fields when calling `/saved/{kind}/{id}`.
- Dates are ISO-ish strings (`YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:SS`). The API
  already filters by date windows; the UI only needs to display them.
- CORS is wide open (`*`) on the backend, so a dev server on any port works.
- The chat endpoint is the only stateful one (per `session_id`); every other
  endpoint is idempotent reads/actions.
