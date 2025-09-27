# Architecture — Runs, Scheduler, and Data Flow

Audience: New engineers. This document explains how Streams are created, how runs are scheduled and executed, how results are stored, and which API endpoints the frontend calls.

## System Overview
- Frontend (Vite + React): User-facing app for auth, creating Streams, browsing runs. See `frontend/`.
- Backend (FastAPI): APIs for profiles and streams; scheduler and workers; orchestrates agents. See `backend/src/app`.
- Database (Supabase/Postgres): Auth users and application tables (profiles, streams, urls registry, curation_runs, clusters, links). See `backend/migrations/` and `docs/backend-schema.md`.
- Agent (default: Surfer): Long-running browsing service (separate Docker app) that performs exploratory web sessions and returns findings. See `docs/surfer-docker-integration.md` and `docs/surfer-docker-service-api.md`.
- Legacy Agent (search-only): Exa-based search pipeline kept for back-compat. See `docs/search-only-plan.md`.

## Core Concepts
- Stream: A user-defined mission with optional source hints and a cadence. Creates a schedule on save.
- Schedule: Defines when to run. Tied to a Stream via `schedules.meta.stream_id`. Also records the default `agent` (e.g., `surfer_v1`).
- Job: Enqueued unit of work derived from a schedule or ad‑hoc Run Now. Contains a `payload` (agent selection, stream_id, params).
- Run: An execution record for a job. On success it persists curations (clusters + links) for the Stream.
- URL Registry: Global table deduping URLs and keeping last-known metadata (domain, title, description, published_at).

## Data Model (Where to look)
- SQL migrations: `backend/migrations/*.sql`
- Human-readable schema: `docs/backend-schema.md`
- Key tables:
  - `profiles`, `streams`, `urls`, `curation_runs`, `curation_clusters`, `curation_cluster_links`, plus scheduler tables `schedules`, `jobs`, `runs`.

## End-to-End Lifecycle
1) Create Stream (Frontend → Backend)
   - Frontend calls `POST /streams` with `{ mission, sources?, cadence }`.
   - Backend stores the row in `streams` and creates a `schedules` row with `meta.stream_id` and `meta.agent='surfer_v1'` (default).

2) Scheduling (Ticker)
   - A background ticker selects due schedules (`active`, `next_run_at <= now`) and enqueues jobs into `jobs` with a deterministic idempotency key.
   - Code: `backend/src/app/scheduler/ticker.py` (env: `SCHEDULE_POLL_INTERVAL_MS`, `SCHEDULE_MAX_JOBS_PER_TICK`).

3) Execution (Worker → Dispatcher → Agent)
   - The worker claims a queued job and starts a `runs` row.
   - Dispatcher selects the agent:
     - `surfer_v1` (default): `backend/src/app/agents/surfer_workflow.py`
     - legacy search-only: `backend/src/app/agents/search_workflow.py`
   - Surfer agent flow:
     - Build prior context from recent runs.
     - Use LLM to generate a concise instruction + context for the Surfer service.
     - Submit to Surfer, poll status, fetch results `{ curations: [{ summary, links[] }] }`.
     - Remix via LLM into curations with `title`, `body_md`, and explicit `links`.
     - Persist `curation_runs`, `curation_clusters`, and `curation_cluster_links`. Ensure each link resolves to a URL in `urls`.

4) Serving Results (Backend APIs)
   - Latest run for a Stream: `GET /streams/{id}/latest`
   - Paginated run history: `GET /streams/{id}/runs?limit=10&before=<iso>`
   - Edit or delete Stream: `PUT /streams/{id}`, `DELETE /streams/{id}` (soft delete disables schedule).
   - Run Now: `POST /streams/{id}/run` (enqueues a job immediately).

5) Frontend Consumption
   - Streams page: `GET /streams` (lists user streams, includes `latest_run_at` when available).
   - Stream view: fetches `GET /streams/{id}/runs` (infinite scroll) and renders curations using markdown bodies (`body_md`) and link chips.

## Runtime Modes
- In-App Scheduler (dev convenience): FastAPI process starts a background thread. Toggle with `SCHEDULER_IN_APP=1`. Entry: `backend/src/app/run_backend.py`.
- Split Processes (recommended): Run API and worker separately.
  - API: `uvicorn app.main:app`
  - Worker: `python -m app.scheduler.worker_main`
- Surfer Service: Runs as a separate Docker service (default `http://127.0.0.1:8001`). Configure with `SURFER_*` envs.

## Failure, Retry, Idempotency
- Ticker uses idempotency keys to avoid enqueueing duplicates per schedule/time window.
- Worker records `attempts`, `status` on `jobs` and `runs`. Surfer client handles 409/timeout and propagates errors.
- On success, a single `curation_run` is written per job; clusters/links attach to that run.

## Security & Auth
- Backend verifies Supabase JWTs on all user-scoped endpoints (Bearer token, audience `authenticated`). See `backend/src/app/auth.py`.
- RLS policies protect user-owned tables. Server-side operations that need elevated access use the service-role client.
- Frontend obtains a Supabase access token (password grant in dev or via supabase-js in future) and sends it in `Authorization` headers.

## Local Development
- Backend environment: `docs/backend-environment.md` (variables and examples). Create a `backend/.env` with your Supabase and provider keys.
- Surfer service: `docs/surfer-docker-integration.md` (Docker compose) and `docs/surfer-docker-service-api.md` (HTTP endpoints).
- Test token: the repo includes a development script to mint a Supabase user token. See backend README and ENV docs.

## Reference Map
- Backend app entry: `backend/src/app/main.py`
- Scheduler: `backend/src/app/scheduler/{ticker.py, worker.py, worker_main.py, jobs.py}`
- Agents: `backend/src/app/agents/{dispatcher.py, surfer_workflow.py, search_workflow.py}`
- Repos: `backend/src/app/repositories/{streams_repo.py, curations_repo.py, urls_repo.py, profile_repo.py}`
- LLM adapter: `backend/src/app/llm/*`, Surfer prompts: `prompts_surfer.py`
- API routes: `backend/src/app/routes/{streams.py, profile.py}`

## Glossary
- Cadence: When a Stream should run (labels like `daily|3xweek|weekly|discovery`, or ISO8601 intervals like `PT30M`).
- Curation: A cluster of related links with a title and descriptive body (`body_md`).
- Agent: The implementation that performs the run. `surfer_v1` is default; search-only is legacy.
