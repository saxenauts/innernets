# InnerNets Backend (Docs-first)

This folder contains backend code and pointers to central docs in `docs/`. See:
- `AGENTS.md` — backend guidelines
- `../docs/backend-environment.md` — environment variables and configuration
- `../docs/backend-schema.md` — evolving database schema
- `../docs/backend-llm-adapter.md` — LLM provider adapter spec
- `../docs/backend-scheduler.md` — scheduler and jobs design
- `../docs/backend-roadmap.md` — milestones and task list
 - Architecture overview (end‑to‑end): `../docs/architecture-runs-scheduler.md`

Code
- `src/app/main.py` — FastAPI app with health endpoint
- `src/app/config.py` — minimal environment loader
- `src/app/supabase_client.py` — Supabase client factory (service role)
- `src/app/models.py` — Pydantic models (Profile)
- `src/app/auth.py` — Supabase JWT verification for `Authorization: Bearer` tokens
- `src/app/repositories/profile_repo.py` — Supabase repository for profiles
- `src/app/routes/profile.py` — Profiles endpoints (GET/PUT `/me/profile`)
- `src/app/llm/*` — Function-first LLM adapter (providers, tools, types)
- `src/app/clients/exa_client.py` — Thin wrapper over `exa-py` for workers (no public routes)
- `tests/` — pytest tests for health, profiles, client creation, and LLM adapter
 - Search workflow core:
   - `src/app/llm/prompts.py` — centralized double‑braced templates (system + user prompts)
   - `src/app/llm/search_steps.py` — Pydantic schemas + wrappers for LLM steps
 - `src/app/agents/search_workflow.py` — orchestration (IDs only to LLM; Exa routing)
- `src/app/agents/surfer_workflow.py` — orchestration for Surfer Docker service (LLM → instruction+context → submit/poll → remix final markdown feed)
- `src/app/scheduler/finalizer.py` — background reconciler that finalizes Surfer jobs that finish after timeouts
 - `src/app/agents/dispatcher.py` — routes jobs to either Surfer or legacy Exa workflow

Service Plan
- Search-only agent loop lives in `docs/search-only-plan.md`.

Development (Poetry)
- Install Poetry: https://python-poetry.org/docs/
- Install deps: `cd backend && poetry install`
- Env: from repo root, create `.env` from `.env.dev` and fill values: `cp .env.dev .env`
- Run tests: `poetry run pytest`
- Run API only: `poetry run uvicorn app.main:app --reload`
  - Or run API + in‑app scheduler (single process): `poetry run python -m app.run_backend`
    - This enables a background scheduler thread via `SCHEDULER_IN_APP=1`.
  - Split processes (recommended for realism):
    - API: `poetry run uvicorn app.main:app --reload`
    - Worker: `poetry run python -m app.scheduler.worker_main`
  - Procfile (optional, for honcho/foreman):
    - `web: poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000`
    - `worker: poetry run python -m app.scheduler.worker_main`
    - Run: `poetry run honcho start -f Procfile` (if installed).
  - Auth: pass `Authorization: Bearer <supabase_access_token>` when calling `/me/profile`.
  - Get the token from your frontend session or Supabase Auth, and set `SUPABASE_JWT_SECRET` in `backend/.env`.
  - Audience: tokens from Supabase use `aud: "authenticated"`. Backend verifies this by default; override with `SUPABASE_JWT_AUD` if needed.
  - Loading env: start from `backend/` or set `DOTENV_PATH=backend/.env` if starting from repo root.

Dev Runbook (staging-ready)
- Prereqs: Python 3.11+, Poetry, Supabase project (URL, keys), Surfer Docker service.
- Env: `cp backend/.env.example backend/.env` and fill SUPABASE_* + SURFER_*; set `CORS_ALLOW_ORIGINS` to your frontend origin.
- Migrations: apply SQL in `backend/migrations/` in order (0001 → 0005) via Supabase SQL Editor. Verify `runs_job_id_unique` index exists.
- Start
  - Simple (single process): `poetry run python -m app.run_backend` (enables in‑app scheduler)
  - Split (recommended):
    - API: `poetry run uvicorn app.main:app --reload`
    - Worker: `poetry run python -m app.scheduler.worker_main`
- Token: `backend/supa_mint_test_token.sh` to mint a short‑lived dev token. Use as `Authorization: Bearer <token>`.
- Quick checks
  - `GET /healthz` returns `{ "ok": true, "surfer_ok": true|false }`
  - `POST /streams` with `{ mission, cadence: "weekly" }` creates a Stream
  - `POST /streams/{id}/run` enqueues a job (returns `{ job_id, status: "queued" }`)

Migrations Runbook (short)
- Apply in order:
  1) 2025-08-26_0001_profiles.sql
  2) 2025-08-27_0002_scheduler.sql
  3) 2025-08-29_0003_streams_curations_urls.sql
  4) 2025-09-25_0004_curation_body_md.sql
  5) 2025-09-27_0005_runs_job_id_unique.sql
- Verify:
  - Unique: `runs(job_id)` — idempotency
  - RLS enabled on profiles, streams, curation_*; urls has SELECT policy
  - Helpful indexes present (see migration SQL)

Surfer Docker Integration
- Start the Surfer service from its repo (Docker). See `docs/surfer-docker-integration.md`.
- Set `SURFER_BASE_URL` in `backend/.env` to its host:port (avoid port 8000 collision with this backend).
- In dev, `SURFER_USE_MOCK=1` will use `/api/explorer/mock` for fast wiring.
- Streams created via `/streams` default their schedule `meta.agent` to `surfer_v1`. Scheduler payloads inherit this and the dispatcher runs `surfer_workflow` accordingly.
- The workflow performs two LLM steps: first to author the Surfer instruction+context (task-first XML prompt), second to remix Surfer’s `{summary, links[]}` into a markdown body (`body_md`) per curation with explicit links.

Long-running jobs
- Surfer typically runs 5–25 minutes (may be longer). The worker polls status every `SURFER_POLL_INTERVAL_S` seconds and persists a `curation_run` upon completion. A Finalizer loop also reconciles late completions (e.g., sleep/long jobs) by checking Surfer and persisting results if the worker previously timed out.
- For prod, run API and worker separately. Ensure the worker and finalizer have network access to the Surfer service.

Next
- Add logging strategy, DB migrations, scheduler worker, and expand LLM adapter (retries, rate limits, cost est.).

Scheduler & Jobs (dev bring-up)
- Apply migration 0002 in Supabase (SQL Editor): `backend/migrations/2025-08-27_0002_scheduler.sql`.
- Add a test user token to `backend/.env` as `DEV_TEST_USER_TOKEN` (do not commit real tokens).
- Enqueue and run jobs via the dev worker loop in tests (`backend/tests/test_jobs_worker.py`).
- The agent workflow lives at `src/app/agents/search_workflow.py` and orchestrates Exa + LLM for a deterministic search flow.

Search Workflow Quickstart
- Generate 5 queries → Exa search per query (25) → filter all candidates (IDs only, 2–3) → read contents → propose 3–6 follow‑ups → Exa again → consolidate into curations.
- LLMs never see URLs; we assign short IDs ("01", "02", …) and map back to URLs in code.
- Temperature is fixed to 1.0 across steps for reliable structured JSON.

Live Full‑Trace Test (real providers)
- Prereq: set `EXA_API_KEY` and Azure OpenAI vars in `backend/.env`.
- Run:
  - `cd backend`
  - `export RUN_LIVE_OPENAI_TESTS=1`
  - `poetry run pytest -q -m live -s tests/test_search_workflow_live.py::test_live_full_trace_personal_ai_dashboard_companies`
- The test prints each step’s prompt (with substitutions), raw JSON outputs, Exa calls, ID assignment, and curations.

Output Shape (for frontend)
- Final object (curations): `[{ title, body_md, links: [{ url, title?, domain }], position, hook? }, …]`.
- `hook` is deprecated. Prefer `body_md` for rendering; the backend still provides `hook` as a short teaser for older runs.

Frontend Integration (next steps)
- Auth: wire Supabase JWT to backend (`Authorization: Bearer <token>`) for any user‑scoped endpoints.
- Streams: add Stream model/endpoints (mission, cadence) and create schedules from the frontend.
- Results: read endpoints return `title`, `body_md`, and resolved `links`. The frontend renders markdown via `react-markdown` and chips for links.
## Streams API (Preview)

All endpoints require `Authorization: Bearer <supabase_access_token>`.

- POST `/streams`
  - Body: `{ "mission": string, "sources"?: string, "cadence": string, "time_zone"?: string }` (sources stored as `sources_hints`)
  - Creates a stream and its schedule; returns the stream row.

- GET `/streams`
  - Lists your streams and includes `latest_run_at` if available.

- GET `/streams/{id}`
  - Returns a single stream.

- PUT `/streams/{id}`
  - Body: `{ mission?, sources?, cadence?, time_zone?, active? }` — updates the stream and syncs the schedule.

- POST `/streams/{id}/run`
  - Enqueues an ad-hoc run; returns `{ job_id, status: 'queued' }`.

- GET `/streams/{id}/latest`
  - Returns the latest curation run with `curations: [{ title, hook, links: [{ url, title?, domain }], position }]`.

Notes
- In dev, the in-app scheduler thread will claim and execute jobs. In prod, run a separate worker and disable in-app scheduler for the API process.

### CORS
- Dev origin allowed by default: `http://localhost:5173`.
- Override with `CORS_ALLOW_ORIGINS` (comma-separated), e.g.:
  - `CORS_ALLOW_ORIGINS=http://localhost:5173,http://127.0.0.1:5173`
