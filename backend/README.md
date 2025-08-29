# InnerNets Backend (Docs-first)

This folder contains backend planning docs and evolving specs, plus a minimal FastAPI app. See:
- `AGENTS.md` — guidelines and architecture
- `ENVIRONMENT.md` — environment variables and configuration
- `SCHEMA.md` — evolving database schema
- `LLM_ADAPTER.md` — LLM provider adapter spec
- `SCHEDULER.md` — scheduler and jobs design
- `TODO.md` — milestones and task list

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
    - `web: poetry run python -m app.run_backend`
    - `worker: poetry run python -m app.scheduler.worker_main`
    - Run: `poetry run honcho start -f Procfile` (if installed).
  - Auth: pass `Authorization: Bearer <supabase_access_token>` when calling `/me/profile`.
  - Get the token from your frontend session or Supabase Auth, and set `SUPABASE_JWT_SECRET` in `backend/.env`.
  - Audience: tokens from Supabase use `aud: "authenticated"`. Backend verifies this by default; override with `SUPABASE_JWT_AUD` if needed.
  - Loading env: start from `backend/` or set `DOTENV_PATH=backend/.env` if starting from repo root.

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
- Final object (curations): `[{ title, hook, link_ids: ["01","02","03"] }, …]`
- Backend holds ID↔URL mapping internally. Next step is to expose an API that returns curations and resolves IDs → URLs.

Frontend Integration (next steps)
- Auth: wire Supabase JWT to backend (`Authorization: Bearer <token>`) for any user‑scoped endpoints.
- Streams: add Stream model/endpoints (mission, cadence) and create schedules from the frontend.
- Results: add a read endpoint to fetch latest run’s curations for a stream (include URL mapping).
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
