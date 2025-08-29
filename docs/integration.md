# Integration Plan — Streams, Auth, Curation Storage, and API

Owner: Backend + Frontend
Status: Proposal (awaiting approval)
Scope: Wire frontend to backend with basic auth, define data model for Streams (mission, sources, cadence), persist curated run results, and introduce a URL registry. Expose APIs so the frontend replaces mocks with live data.

---

## Goals
- Frontend uses backend APIs (no mocks) with a test user token during dev.
- Persist user Streams and their curated runs. Each run stores curations (clusters with titles, hooks, and link refs).
- Create a URL registry table to de-duplicate and reference links across runs/streams/users (indexing/search later).
- Add minimal endpoints for CRUD on streams, trigger runs, and fetch latest curations for display with dates.
- Keep implementations small, schema-first, and RLS-safe.

---

## Current State (as of repo)

Backend
- FastAPI app: `backend/src/app/main.py` with `/healthz` and `/me/profile`.
- Auth: Supabase JWT verification in `backend/src/app/auth.py` (Bearer). Test token mint script: `backend/supa_mind_test_token.sh`.
- Supabase clients: service-role and user-token variants in `backend/src/app/supabase_client.py`.
- DB: migrations for `profiles` and scheduler (`schedules`, `jobs`, `runs`) with RLS. See `backend/migrations/*`.
- Search workflow: ID-first orchestration in `backend/src/app/agents/search_workflow.py` calling LLM steps in `backend/src/app/llm/search_steps.py` and Exa via `backend/src/app/clients/exa_client.py`.
- LLM adapter: structured outputs via Azure/OpenAI, prompts centralized in `backend/src/app/llm/prompts.py`.
- No persistence yet for streams/curations/urls; scheduler runs are not tied to user streams.

Frontend
- Pages: `Login`, `Onboarding` (captures mission/sources/cadence), `Streams` (lists mock topics), `StreamView` (shows mock items). See `frontend/src/pages/*`.
- State: localStorage-backed `AuthProvider` (`frontend/src/state/auth.tsx`). No backend calls yet.
- Mock data: `frontend/src/mocks/mock-data.ts`.

---

## High-Level Phases
1) Basic Auth (Dev) and API skeleton
2) Data Model + Migrations (streams, curations, urls)
3) Backend Repositories + Routes
4) Worker integration to persist run outputs (Procfile/runtime aware)
5) Frontend integration (replace mocks)
6) Tests and docs

Each phase is shippable and small. RLS policies are included where relevant.

---

## Phase 1 — Basic Auth (Dev) and API Skeleton

Decisions
- Keep Supabase Bearer JWT (already implemented). For dev, use a minted test user token.
- Frontend passes `Authorization: Bearer <token>` for all API calls.

Actions
- Developer runbook: use `backend/supa_mind_test_token.sh` to mint a test token. Document curl examples in `backend/README.md` (dev-only section).
- Backend no-op endpoints to verify auth before implementing core logic:
  - `GET /me/profile` (exists) — use to test token roundtrip.
  - `GET /healthz` — basic health.

Frontend prep
- Add a small fetch wrapper that injects `Authorization` from localStorage (key: `in_test_bearer`), with a dev-only input on Login to paste the token (temporary).
  - Pointer: implement in `frontend/src/lib/api.ts` and call from pages. Replace later with real Supabase auth.

---

## Phase 2 — Data Model + Migrations

Tables (Postgres/Supabase)
- `public.streams`
  - `id uuid pk default gen_random_uuid()`
  - `user_id uuid not null references auth.users(id) on delete cascade`
  - `mission text not null`
  - `sources_hints text null` (freeform hints)
  - `cadence text not null` (e.g., `daily|3xweek|weekly|discovery|cron` string)
  - `time_zone text not null default 'UTC'`
  - `active boolean not null default true`
  - `meta jsonb not null default '{}'`
  - `created_at timestamptz not null default now()`, `updated_at timestamptz not null default now()`
  - RLS: owner-only full access (select/insert/update/delete) where `auth.uid() = user_id`.

- `public.urls` (global URL registry; backend-managed)
  - `id uuid pk default gen_random_uuid()`
  - `url text not null` (normalized canonical URL)
  - `domain text not null`
  - `last_title text null`
  - `last_description text null` (short description/summary if available)
  - `last_published_at timestamptz null`
  - `first_seen_at timestamptz not null default now()`
  - `last_seen_at timestamptz not null default now()`
  - `meta jsonb not null default '{}'`
  - Constraint: enforce uniqueness on normalized URL to avoid duplicates (implementation detail: unique constraint on lower(url)).
  - Access: backend writes via service role; clients read through API responses (no direct client writes).

- `public.curation_runs` (per stream run; stores overall output from search workflow)
  - `id uuid pk default gen_random_uuid()`
  - `stream_id uuid not null references public.streams(id) on delete cascade`
  - `job_id uuid null references public.jobs(id) on delete set null` (if run via scheduler)
  - `status text not null default 'succeeded'` (`running|succeeded|failed|canceled`)
  - `started_at timestamptz not null default now()`
  - `finished_at timestamptz null`
  - `metrics jsonb not null default '{}'` (reads, costs, token usage)
  - `raw jsonb null` (optional: debug-only pruning; consider not storing LLM prompts)
  - RLS: readable if `stream.user_id = auth.uid()`. Writes guarded via backend using user token.

- `public.curation_clusters` (curation = cluster)
  - `id uuid pk default gen_random_uuid()`
  - `run_id uuid not null references public.curation_runs(id) on delete cascade`
  - `title text not null`
  - `hook text not null`
  - `position int not null` (for ordering)
  - RLS: join through `curation_runs` to `streams` for ownership.

- `public.curation_cluster_links`
  - `id uuid pk default gen_random_uuid()`
  - `cluster_id uuid not null references public.curation_clusters(id) on delete cascade`
  - `url_id uuid not null references public.urls(id) on delete restrict`
  - `snapshot_title text null` (optional, store the title as seen during this run)
  - `position int not null`
  - RLS: join through cluster → run → stream for ownership.

Policies
- Enable RLS on all user-owned tables. Owner-only policies similar to `profiles` and `schedules`.

Notes
- We intentionally avoid storing ephemeral short IDs. We map them to `url_id` via the registry at persistence time and update `urls.last_seen_at` and metadata (title/description) when available.
- Indexes: add composite indexes for `curation_runs(stream_id, started_at desc)` and for cluster ordering; maintain a uniqueness constraint on normalized `urls.url`.

---

## Phase 3 — Backend Repositories + Routes

Repositories (Supabase clients)
- `backend/src/app/repositories/streams_repo.py`
  - `create_stream(user_id, token, fields)` → row
  - `list_streams(user_id, token)` → rows
  - `get_stream(stream_id, user_id, token)` → row
  - `update_stream(stream_id, user_id, token, fields)` → row

- `backend/src/app/repositories/urls_repo.py`
  - `ensure_url(url, title=None, description=None, published_at=None, domain=None)` → url row (idempotent upsert by normalized url)
  - `bulk_ensure(urls: List[...])` → list of `{ url, url_id }`

- `backend/src/app/repositories/curations_repo.py`
  - `create_run(stream_id, status='running', metrics={})` → run row
  - `complete_run(run_id, metrics)` → run row
  - `insert_clusters(run_id, clusters)` → rows
  - `insert_cluster_links(cluster_id, link_refs)` → rows, each `{ url_id, snapshot_title?, position }`
  - `get_latest_run(stream_id)` → run + clusters + links (joined)
  - `list_runs(stream_id, limit=10, offset=0)`

Routes (FastAPI)
- `POST /streams` — create stream
  - Body: `{ mission, sources?, cadence }` (sources stored as `sources_hints`)
  - Behavior: creates the stream and an associated `schedules` row using the given cadence and time_zone (default UTC).
  - Returns: stream row (id, created_at, etc.)

- `GET /streams` — list my streams
- `GET /streams/:id` — get stream
- `PUT /streams/:id` — update mission/sources/cadence/active
  - Behavior: if `cadence` or `time_zone` changes, update the associated schedule accordingly (or disable if `active=false`).

- `POST /streams/:id/run` — trigger an immediate run (enqueue a job)
  - Response: `{ job_id, status }`

- `GET /streams/:id/latest` — return latest curation run with clusters and resolved URLs
  - Response example:
    ```json
    {
      "run_id": "...",
      "run_at": "2025-08-29T12:34:56Z",
      "curations": [
        {"title": "...", "hook": "...", "links": [{"url": "https://...", "title": "...", "domain": "..."}]}
      ]
    }
    ```

- `GET /streams/:id/runs?limit=10&offset=0` — list runs (for a history view)

Implementation pointers
- Create `backend/src/app/routes/streams.py` and include router in `main.py`.
- Reuse `get_current_user_id` and `get_current_token` dependencies to supply user scope and RLS-protected user clients.

---

## Phase 4 — Worker Integration (Persist Run Outputs)

Flow
1) Enqueue job for a stream:
   - Job payload: `{ type: 'stream_run', stream_id: <uuid> }`.
2) Worker receives job → loads stream (mission/sources) → calls search workflow with mission and routes.
3) As soon as run starts, create a `curation_runs` row with `status='running'` (content-run). Note: the scheduler already creates an infra `runs` row via `jobs.start_run(job_id)` when the job is claimed; we will keep both (infra run for executor metrics, curation run for user-visible history).
4) After workflow completes, map ephemeral IDs to `url_id`s via the registry (upsert `urls` as needed), then write `curation_clusters` and `curation_cluster_links` in a transaction.
5) Update `curation_runs.status='succeeded'`, set `finished_at`, and store metrics (`cost_exa`, token usage) into `metrics`.

Changes in code (where)
- Add a small dispatcher in `backend/src/app/scheduler/jobs.py` to handle `stream_run` by stream_id and call `agents.search_workflow.run`.
- Extend `agents.search_workflow.run` to accept either `payload.params.mission` (current) or `payload.stream_id`: when stream_id is present, load mission/sources and set `params.mission` accordingly. Keep existing signature but branch on payload.
- On success, call `curations_repo` to persist. Keep raw prompts/outputs out of DB for now (privacy/cost); metrics only.

Observability
- Log `user_id`, `stream_id`, `job_id`, `run_id`, `cost.total`, and counts. Use `logging.getLogger('app.search_workflow')` pattern already present.

Runtime & Procfile (how runs are created and executed)
- Procfile (`backend/Procfile`) defines:
  - `web`: `poetry run python -m app.run_backend` — starts FastAPI and, by default, enables an in‑app scheduler thread via `SCHEDULER_IN_APP=1` (see `app.main` and `app.scheduler.runner`). The thread ticks schedules and calls `run_once(...)` to claim and execute jobs, creating infra `runs` rows at claim time.
  - `worker`: `poetry run python -m app.scheduler.worker_main` — dedicated worker loop; recommended for production and scaling.

- Recommended modes:
  - Development: run only `web` (in‑app scheduler enabled). `POST /streams/:id/run` enqueues a job; the background thread will process it and create both `runs` and `curation_runs` rows.
  - Production: run both `web` and `worker`. Set `SCHEDULER_IN_APP=0` on `web` to disable the in‑app scheduler loop and avoid duplication. Scale `worker` as needed.

- API-triggered runs vs scheduled runs:
  - `POST /streams/:id/run` enqueues an ad‑hoc job immediately (bypasses ticker timing) and returns 202.
  - Scheduled runs come from `ticker.tick()` advancing due `schedules` and enqueuing jobs. Either the in‑app scheduler thread or a worker loop that calls `tick()` can perform this (we already do the former in dev; in prod, prefer doing it in a dedicated worker or a single leader instance).

- “Create a run inside FastAPI”
  - We do not pre-create `runs` inside HTTP routes. The infra `runs` row is created at job claim (`jobs.start_run`) to preserve exactly‑once processing and avoid orphaned runs.
  - The content `curation_runs` row is also created by the worker at execution start. Routes return quickly and the UI polls for results.
  - Optionally, a dev-only `?mode=sync` could execute inline for quick iteration, but it’s not recommended for production.

---

## Phase 5 — Frontend Integration (Replace Mocks)

Auth (Dev)
- On Login, show an optional text area to paste a test token (stores to `localStorage.in_test_bearer`). Keep email/password fields for now (no effect).
- Fetch wrapper: `frontend/src/lib/api.ts` exporting `api.get/post/put`, injecting `Authorization` from storage.

Onboarding → Create Stream
- Replace localStorage persistence with `POST /streams`.
- After creation, navigate to `/streams/:id`.
- Present a “Run now” button that calls `POST /streams/:id/run` and then polls `GET /streams/:id/latest` until a run appears (or show a link to background run if the scheduler is used).

Streams list
- Replace mock list with `GET /streams` and show stream name = derived from mission (first sentence) or a `name` field if we later add one.
- For each stream, display the timestamp of the latest curation run (if any).

Stream view
- Replace mock items with `GET /streams/:id/latest` data.
- Show run date/time. For now, display clusters as simple cards using existing `ItemCard` or a minimal variant: `title`, `hook`, and link chips (first link as the main CTA).
- Remove “list of topics” scaffold.

Design/UX quick wins
- Loading skeletons for streams list and stream view.
- Error toasts on failed API calls (simple `alert` ok for first cut).

---

## Context Wiring (t > 0)

- Streams are fixed definitions (mission, sources/hints, cadence). Each cadence cycle runs the full `search_workflow` and appends new curations to the stream.
- At t=0: no context; at t>0: pass the previous run’s curations as context into LLM steps via the existing `additional_context_json` inputs in `llm/prompts.py`.
- Minimal now: add a nominal repository method `get_previous_context(stream_id)` that returns a compact object, e.g. `{ last_run_at, curations: [ { title, hook?, link_domains: ["..."], link_urls_sample: ["..."] } ] }`.
- Orchestrator change: when `payload.stream_id` is present, load this context and pass it to `generate_search_queries`, `filter_candidates`, `propose_followups`, and `consolidate_curations`. For t=0, pass `{}`.

---

## Phase 6 — Tests and Docs (Updated)

Backend tests
- Unit: repositories (streams, urls, curations) with monkeypatched Supabase client.
- API: FastAPI TestClient tests for streams CRUD and latest; auth via a signed JWT (like profile tests).
- Worker: end-to-end mocked run that writes one run with two clusters and verifies joins.

Frontend tests
- Adjust existing tests to drop mocks and stub `fetch` responses for streams API.
- Add a basic test for StreamView rendering a run with date and links.

Docs
- Update `backend/SCHEMA.md` with the new tables and RLS.
- Update `backend/SUPABASE_RUNBOOK.md` with migration steps for new tables.
- Add API reference to `backend/README.md`.
- Add `frontend/README.md` with Vite env setup (VITE_API_BASE_URL, VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY), login flow, and Streams endpoints usage.

---

## API Shapes (for frontend reference)

`GET /streams`
- Response: `[{ id, mission, sources_hints, cadence, created_at, updated_at, latest_run_at? }]`

`POST /streams`
- Body: `{ mission: string, sources_hints?: string, cadence: string }`
- Response: `{ id, mission, sources_hints, cadence, created_at }`

`GET /streams/:id`
- Response: `{ id, mission, sources_hints, cadence, created_at, updated_at }`

`PUT /streams/:id`
- Body: `{ mission?, sources_hints?, cadence?, active? }`
- Response: stream row

`POST /streams/:id/run`
- Semantics: enqueues an ad‑hoc job and returns immediately (202). Execution happens in background (in‑app scheduler in dev, or the dedicated worker in prod).
- Response: `{ job_id: string, status: 'queued' }`

`GET /streams/:id/latest`
- Response: `{ run_id, run_at, curations: [{ title, hook, links: [{ url, title?, domain }], position }], started_at?, finished_at? }`

---

## Open Questions / Risks
- Global URL registry/indexing is deliberately deferred; current plan stores raw URLs per curation. Revisit when we add cross-stream URL semantics.
- Where to store prior LLM prompts/outputs if at all? For now, don’t store; add a debug flag to log to blob if needed.
- Scheduling: create a `schedules` row per stream automatically on POST /streams; keep in sync if cadence changes (update or disable schedule on stream update).
- Naming: do we want a user-editable stream `name` separate from `mission`? Suggest deferring; derive a compact name from mission until product decides.
- Cadence format: keep as friendly strings now; consider CRON or ISO8601 later with validation.

---

## Milestone Checklist

M0 — Auth + Skeleton
- [ ] Dev token pasted in frontend; simple `api.ts` wrapper
- [ ] Verify `/me/profile` with token from browser

M1 — Schema
- [ ] Migrations: `streams`, `urls`, `curation_runs`, `curation_clusters`, `curation_cluster_links` (+ RLS)
- [ ] Runbook updated; apply in Supabase

M2 — Backend
- [ ] Repositories implemented
- [ ] Routes: `/streams`, `/streams/:id`, `/streams/:id/run`, `/streams/:id/latest`

M3 — Worker
- [ ] Job type `stream_run` wired; persists one run end-to-end
- [ ] Metrics recorded (`cost_exa`, `reads`, tokens)

M4 — Frontend
- [ ] Onboarding → `POST /streams`
- [ ] Streams list → `GET /streams`
- [ ] Stream view → `GET /streams/:id/latest`
- [ ] Remove mock topics

M5 — Tests + Docs
- [ ] Backend unit + API tests
- [ ] Frontend tests updated
- [ ] Docs updated (schema, API, runbook)

---

## Implementation Pointers (files/dirs)
- Backend
  - Repos: `backend/src/app/repositories/{streams_repo.py,urls_repo.py,curations_repo.py}`
  - Routes: `backend/src/app/routes/streams.py` (include in `main.py`)
  - Scheduler: `backend/src/app/scheduler/jobs.py` add handler for `stream_run`
  - Agent: extend `agents/search_workflow.run` to accept `payload.stream_id`

- Frontend
  - `frontend/src/lib/api.ts` — fetch wrapper
  - `frontend/src/pages/Onboarding.tsx` — POST stream
  - `frontend/src/pages/Streams.tsx` — GET streams
  - `frontend/src/pages/StreamView.tsx` — GET latest
  - Remove `frontend/src/mocks/mock-data.ts`; migrate `ItemCard` to accept API shape

---

## After V1 (not in scope here)
- URL search/embedding index over the registry (domains, tags, embeddings)
- Stream memory: feed prior curations and user actions into `additional_context_json`
- Actions: Save/Hide/More-like with user feedback tables
- Observability: central request IDs; stats dashboards
