# Repo Cleanup Plan — InnerNets

Purpose: Make the codebase and docs consistent, production‑ready, and easy to operate. This list aggregates missing pieces, outdated docs, gaps, and polish items discovered across the monorepo. After approval, we will execute these in small PRs.

## Repo & Docs
- [x] Create a canonical "Runs & Scheduler" architecture doc (end‑to‑end): Stream → Schedule → Job → Worker → Agent (Surfer default) → DB → APIs → Frontend. Include in‑app vs split‑process runtime, sequence diagrams, and failure modes. Place at `docs/architecture-runs-scheduler.md`.
- [x] Audit and update outdated/duplicative docs:
  - [x] `docs/integration.md`: Current State is stale (now have streams/urls/curations + scheduler tied to streams). Update to reflect implemented APIs and persistence.
  - [x] `docs/search-only-plan.md`: Mark as “Legacy plan (Exa-first)” with a header note; link to Surfer default. Keep for context, not as current plan.
  - [x] `docs/Phase-1.md`: Mark as historical (search‑only MVP). Either move to `docs/archive/` or add a warning banner.
  - [x] Consolidate repeated “Search Loop” prose that appears in multiple docs into one canonical reference, and cross‑link.
  - [x] Consolidate scattered backend docs into `docs/` and remove duplicates from `backend/`:
    - Moved `backend/ENVIRONMENT.md` → `docs/backend-environment.md`
    - Moved `backend/SCHEDULER.md` → `docs/backend-scheduler.md`
    - Moved `backend/SCHEMA.md` → `docs/backend-schema.md`
    - Moved `backend/LLM_ADAPTER.md` → `docs/backend-llm-adapter.md`
    - Moved `backend/EXA_USAGE.md` → `docs/backend-exa-usage.md` (marked legacy/optional)
    - Moved `backend/SUPABASE_RUNBOOK.md` → `docs/backend-supabase-runbook.md`
    - Moved `backend/TODO.md` → `docs/backend-roadmap.md`
    - Moved `frontend/design.md` → `docs/frontend-design.md`
  - [x] Updated cross-links in `docs/architecture-runs-scheduler.md`, `docs/integration.md`, `backend/AGENTS.md`, `backend/README.md`, `README.md`, and `docs/updates.md` to point to the new locations.
- [ ] Add missing backend env templates referenced by docs:
  - [x] `backend/.env.example` with all keys (SUPABASE_*, SURFER_*, AZURE_OPENAI_*, EXA_*, CORS_ALLOW_ORIGINS, etc.).
  - [x] `backend/.env.dev`, `backend/.env.prod` placeholders (no secrets).
 - [x] Fix naming mismatch for test token script: file is `backend/supa_mind_test_token.sh` but referenced as “mint” in places. Standardize on `supa_mint_test_token.sh` (rename file + update references).
- [x] Root README: add a short architecture overview and point to the new Runs & Scheduler doc.
- [ ] Optional hygiene: run `markdownlint` and `prettier` across docs; add notes to AGENTS on maintaining style.


## Backend — Scheduler, Jobs, Worker

Staging focus: correctness and debuggability without full observability. We run exactly one dedicated worker and no in‑app scheduler.

- [x] Enforce single‑worker mode in staging
  - Updated `backend/Procfile` to run API via `uvicorn` (no in‑app scheduler) and one external worker: `poetry run python -m app.scheduler.worker_main`.
  - Added staging snippet and recommended values to `docs/backend-environment.md`.

- [x] Run idempotency (one run per job)
  - Added DB migration `backend/migrations/2025-09-27_0005_runs_job_id_unique.sql` for a unique index on `runs.job_id`.
  - Updated `start_run(job_id)` to use `upsert(..., on_conflict='job_id')` and return the existing run on conflict.

- [x] Minimal execution logs (console)
  - Added log lines with `trace_id`, `job_id`, `run_id`, `schedule_id`, `user_id`, `agent`, `status`, and `elapsed_ms` in the claim/start/finish paths.

- [x] Timeouts verified for Surfer jobs
  - Confirmed `SURFER_MAX_WAIT_S` and `SURFER_POLL_INTERVAL_S` are used by `wait_for_result`; added recommended staging defaults to `docs/backend-environment.md`.

- [x] Graceful shutdown (minimal)
  - `worker_main` now handles SIGTERM/SIGINT and exits the loop promptly between iterations.

Deferred (post‑staging)
- [ ] Atomic job claiming for concurrent workers (single UPDATE … RETURNING pattern)
- [ ] Metrics/observability (queue depth, latencies, success/fail)

## Backend — Surfer Integration
- [x] Unit tests: `agents/dispatcher` routing (payload.agent vs schedule.meta.agent; default to surfer).
- [x] Unit tests: `clients/surfer_client` error/timeout/409 handling; polling backoff and max wait.
- [ ] Optional: internal-only surfacing of Surfer job `status_url`/`logs_url` for ops triage (do not expose to end users).
- [x] backend-environment.md: add a snippet showing a minimal working Surfer config and curl health check; ensure ports don’t collide with backend.

## Backend — API Contracts & Validation
- [x] Add lightweight response models on Streams routes for stable contracts (`/streams`, `/streams/{id}`, `/streams/{id}/latest`, `/streams/{id}/runs`).
  - Implemented inline Pydantic models in `backend/src/app/routes/streams.py` (`StreamOut`, `RunOut`, `CurationOut`, `LinkOut`, `RunsListOut`, `LatestOut`, `EnqueueOut`).
  - Responses now expose `sources` (mapped from DB `sources_hints`) and include `run_at` alias where applicable for back‑compat.
- [x] Input validation (KISS): restrict `cadence` to allowed values only (`daily | 3xweek | weekly | discovery`).
  - Enforced via Enum on `StreamCreate`/`StreamUpdate`.
  - `GET /streams/{id}/runs` now bounds `limit` to 1..25; `before` remains an optional string.
- [x] Health: extend `/healthz` to report Surfer reachability (non‑blocking, fast timeout).
  - Returns `{ ok: true, surfer_ok: true|false }` by probing `${SURFER_BASE_URL}/healthz` with a 300ms timeout.
- [x] Error model: standardized error responses (codes/messages) across routes.
  - Implemented global handlers in `backend/src/app/main.py` for `RequestValidationError`, `HTTPException`, and unexpected errors.
  - Shape: `{ code: string, message: string }` with codes: BadRequest/Unauthorized/Forbidden/NotFound/Conflict/RateLimited/Internal.
  - Added tests: `backend/tests/test_error_model.py`.

## Backend — DB & Migrations

Staging focus: apply existing SQL in order and add only indexes that materially help current queries. Keep `sources_hints` as-is (no rename planned).

- [x] Apply migrations in order on Supabase (SQL Editor):
  - 0001 — `backend/migrations/2025-08-26_0001_profiles.sql`
  - 0002 — `backend/migrations/2025-08-27_0002_scheduler.sql`
  - 0003 — `backend/migrations/2025-08-29_0003_streams_curations_urls.sql`
  - 0004 — `backend/migrations/2025-09-25_0004_curation_body_md.sql`
  - 0005 — `backend/migrations/2025-09-27_0005_runs_job_id_unique.sql`
- [x] RLS in place for all user-facing tables (profiles, streams, curation_*). Verified in the SQL above; no action needed.
- [x] Keep schema field: `streams.sources_hints` retained. API maps `sources` → `sources_hints` for compatibility.
- [ ] Optional post-staging indexes (performance, not required now):
  - JSONB meta lookup on schedules by `stream_id` (used when syncing schedule on stream update/delete):
    - `create index if not exists idx_schedules_meta_gin on public.schedules using gin (meta);`
  - Job queue scan under load (claiming oldest queued):
    - `create index if not exists idx_jobs_status_queued_at on public.jobs (status, queued_at);`
- [ ] Provisioning note: add a short “Migrations Runbook” to backend/README.md describing how to apply the above SQL files in Supabase and verify indexes/policies.

## Backend — Docs & Runbooks
- [x] Backend README: Dev Runbook (necessary for staging)
  - Prereqs: Python 3.11+, Poetry, Supabase project (URL, keys), Surfer Docker service.
  - Env: copy `backend/.env.example` → `backend/.env`, fill SUPABASE_* and SURFER_*; set `CORS_ALLOW_ORIGINS` to frontend origin.
  - Migrations: apply SQL in `backend/migrations/` in numeric order (0001 → 0005). Verify `runs_job_id_unique` exists.
  - Run locally:
    - Option A (simple single process): `poetry run python -m app.run_backend` (enables in‑app scheduler).
    - Option B (recommended for staging): Uvicorn API + separate worker process (see `backend/Procfile`).
  - Mint a dev token: `backend/supa_mint_test_token.sh` and call an endpoint with `Authorization: Bearer <token>`.
  - Quick checks: `/healthz` shows `{"ok": true, "surfer_ok": true|false}`; `POST /streams` works; `POST /streams/:id/run` enqueues.
- [x] Backend README: Migrations Runbook (short)
  - Apply order, how to run in Supabase SQL Editor, and how to verify RLS, indexes, and FK deletes.
- [x] SCHEDULER.md: cross‑link architecture; Surfer default agent, Exa legacy path.

## Backend — Tests

Necessary for staging confidence (fast and minimal):
- [x] Streams contracts & validation
  - Ensure `cadence` enum enforced on create/update (422 on invalid).
  - Response shapes of `GET /streams`, `GET /streams/{id}`, `GET /streams/{id}/latest`, `GET /streams/{id}/runs` match models.
- [x] Runs pagination and joins
  - `GET /streams/{id}/runs` returns `next_cursor` correctly and each curation includes `links` joined via URL registry.
- [x] Health probe
  - Extend `tests/test_health.py` to assert `surfer_ok` true/false by mocking the Surfer health endpoint.
- [x] Surfer settings
  - Tests for `SURFER_POLL_INTERVAL_S`, `SURFER_MAX_WAIT_S`, and `SURFER_USE_MOCK` toggles influencing client behavior.

Already covered (no action):
- [x] Dispatcher routing matrix (payload.agent vs schedule.meta.agent).
- [x] Surfer client polling, 409 backoff, timeouts, failed states.
- [x] Worker enqueue/claim/execute basics.

## Frontend — Auth & API
- [x] Replace manual password grant with `@supabase/supabase-js` to handle token refresh and expiry; wrap in an Auth service.
- [x] Ensure all API calls attach `Authorization` consistently; centralize base URL + auth injection (already in `lib/api.ts`, keep).
- [x] Harden error UX on Login/SignUp; add a minimal banner for backend 401/5xx in Streams/StreamView.
- [x] Add auth tests: session gating (Protected), login/sign-up flows (confirmation disabled/enabled), Streams/StreamView 401 banners.
 - Deferred: consider backend-managed cookie sessions (BFF) to eliminate transient 401s after long idle in SPA flows.

## Frontend — Streams & Runs UX
- [ ] Verify infinite scroll correctness with real `/streams/{id}/runs`; add tests for cursoring and "Load more" fallback.
- [ ] Surface Surfer job/run status while waiting after "Run Now" (optimistic UI); poll latest endpoint briefly.
- [ ] Accessibility pass (ARIA roles on dialogs/menus, focus management, link semantics). Add a quick a11y checklist to `frontend/AGENTS.md`.

## Frontend — Docs & Config
- [ ] Frontend README: add a quick troubleshooting section (CORS, missing envs, 401 from backend).
- [ ] Document required Vite envs and example `.env.local` (already present; confirm values and add Surfer/BFF notes if a proxy is introduced later).

## Tooling & CI
- [ ] Add minimal CI: backend pytest, frontend vitest, markdownlint/prettier checks on docs.
- [ ] Optional: type checking (mypy/pyright) for backend, ESLint for frontend.

## Naming & Consistency
- [ ] Standardize "sources" vs "sources_hints" in APIs/docs (keep adapter in code; plan a schema rename).
- [ ] Ensure all docs use consistent terms: “Stream”, “Run”, “Curation (cluster)”, “URL registry”.
- [ ] Update references from "mint/mind" in token script to the standardized name everywhere.

## Security & Secrets
- [ ] Double‑check no secrets are committed; confirm `.env*` files are gitignored and templates contain placeholders only.
- [ ] Document secret rotation basics and least‑privilege access for service role keys.

## Deployment Prep (tracked but out of scope for this cleanup pass)
- [ ] Containerization strategy for backend worker/API; Surfer is an external Docker service.
- [ ] Environment matrix (dev/staging/prod) and runbooks per environment.
- [ ] Observability hooks (Sentry/OTel) wired and configurable.

---

Notes
- Surfer is now the default agent for Streams; the Exa search‑only workflow remains for back‑compat and can be kept as a "legacy" path. Docs should reflect this clearly.
- Many backend docs already exist (ENVIRONMENT, SCHEDULER, SCHEMA); the biggest doc gap is a single, cross‑cutting Runs & Scheduler architecture write‑up with diagrams.
