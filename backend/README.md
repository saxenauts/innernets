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

Service Plan
- Search-only agent loop lives in `docs/search-only-plan.md`.

Development (Poetry)
- Install Poetry: https://python-poetry.org/docs/
- Install deps: `cd backend && poetry install`
- Env: from repo root, create `.env` from `.env.dev` and fill values: `cp .env.dev .env`
- Run tests: `poetry run pytest`
- Run API (dev): `poetry run uvicorn app.main:app --reload`
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
- The agent loop lives at `src/app/agents/search_loop.py` and currently returns stub metrics; integration with Exa and the LLM adapter is next.
