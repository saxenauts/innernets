# Project Updates and Tasks

Use this document to record natural-language updates and maintain a lightweight task board. Keep entries concise, dated, and linked to issues/PRs where possible.

## Updates Log
- 2025-08-29 — Added reverse‑chronological runs feed: backend supports `GET /streams/:id/runs?limit=10&before=<iso>` (returns runs with clusters+links and `next_cursor`), and frontend StreamView renders a minimal feed with Load more and intersection‑based infinite scroll. (ref: backend/src/app/repositories/curations_repo.py, backend/src/app/routes/streams.py, frontend/src/pages/StreamView.tsx)
- 2025-08-29 — Streams UX polish: added loader skeletons to Streams list to avoid empty flash and removed stray divider when list is empty. Adjusted auth flows: Login now routes to Streams; added Sign up page that routes to Onboarding (Create Stream). Onboarding no longer pre-fills from previous local values. (ref: frontend/src/pages/Streams.tsx, frontend/src/pages/Login.tsx, frontend/src/pages/SignUp.tsx, frontend/src/App.tsx, frontend/src/components/NavBar.tsx, frontend/src/pages/Onboarding.tsx)
- 2025-08-29 — Scheduler hardening: map cadence labels ('daily'/'3xweek'/'weekly'/'discovery') to real intervals; auto-disable the demo schedule named 'e2e-scheduler-demo'; and skip agent execution for jobs without `stream_id` whose params only have `schedule_id` (prevents wasteful demo runs). (ref: backend/src/app/scheduler/ticker.py, backend/src/app/agents/search_workflow.py)
- 2025-08-29 — Removed demo script that created 'e2e-scheduler-demo' schedules and cleaned docs. New sign-ups only create per-stream schedules; no demo schedules are created. (ref: backend/src/app/scheduler/demo.py removed, backend/SCHEDULER.md, backend/ENVIRONMENT.md, backend/AGENTS.md)
- 2025-08-29 — Streams edit/delete: added PUT `/streams/:id` (accepts `mission`, `sources`, `cadence`) and DELETE `/streams/:id` (soft-delete + disable schedule). Frontend StreamView now has Edit and Delete actions with a minimal inline form. Renamed UI copy to “Sources” (was “hints”). Added backend tests for update/delete. (ref: backend/src/app/routes/streams.py, backend/src/app/repositories/streams_repo.py, backend/tests/test_streams_api.py, frontend/src/pages/StreamView.tsx)
- 2025-08-29 — Frontend buttons: added consistent hover effects (lift + shadow + color) across all `Button` variants and the custom `Select` trigger; added a `destructive` button variant for Delete actions. (ref: frontend/src/components/ui/button.tsx, frontend/src/components/ui/select.tsx)
- 2025-08-29 — Streams + URL registry + curations storage implemented; Streams API added (create/list/get/update/run-now/latest). Orchestrator persists runs and maps link IDs to URL registry. Frontend integrated with API: login via Supabase password grant, create streams, list streams, view latest curations, and trigger Run Now. CORS enabled for dev. (ref: backend migrations 0003; backend/src/app/routes/streams.py; backend/src/app/agents/search_workflow.py; frontend src/pages/Login/Onboarding/Streams/StreamView)
- 2025-08-28 — Scheduler runtime integrated: added in-app background scheduler (thread) and standalone worker entrypoint; one-command launcher (`app.run_backend`) and Procfile provided. Ticker hardened with due-filter guard and scheduled payload now hydrated from schedule meta params. Enhanced demo to stress queue and print per-job outputs. (ref: backend/src/app/main.py, backend/src/app/scheduler/{runner.py,worker_main.py,ticker.py,demo.py}, backend/src/app/run_backend.py, backend/Procfile)
- 2025-08-28 — Fixed structured outputs for search workflow: enforced integer 0–100 scoring via prompt update and Pydantic validator (coercion from 0–5 floats). Tightened Azure provider system hint to avoid decimals for integer fields. Added unit test for score coercion. (ref: backend/src/app/llm/schemas.py, backend/src/app/llm/prompts.py, backend/src/app/llm/providers/azure_openai.py, backend/tests/test_llm_schema_coercion.py, backend/src/app/agents/search_workflow.py)
- 2025-08-27 — Refined Exa integration: removed public `/exa/*` routes; workers call `exa-py` directly via `ExaClient`. Updated docs and tests accordingly. (ref: backend/src/app/clients/exa_client.py, backend/EXA_USAGE.md)
- 2025-08-27 — Backend LLM adapter implemented (function-first, Azure); added tool registry, unit tests with mocked HTTP, and updated backend docs/env templates. (ref: backend/src/app/llm/*, backend/tests/test_llm_adapter.py, backend/LLM_ADAPTER.md, backend/ENVIRONMENT.md)
- 2025-08-27 — Scheduler groundwork: added DB schema (schedules, jobs, runs), env hook for dev test user token, and worker/agent stubs to execute jobs. (ref: backend/migrations/2025-08-27_0002_scheduler.sql, backend/src/app/scheduler/*, backend/src/app/agents/search_workflow.py, backend/SCHEDULER.md, backend/ENVIRONMENT.md, backend/TODO.md)
- 2025-08-26 — Refactored Onboarding and missing-state views to shadcn/Tailwind styles; removed legacy class usage causing “old UI”. (ref: frontend/src/pages/Onboarding.tsx, frontend/src/pages/StreamView.tsx)
- 2025-08-26 — Added token-styled Select component and replaced native select for cadence; removed unused CSS/components; aligned Tailwind v4 import; deleted duplicate Tailwind config. (ref: frontend/src/components/ui/select.tsx, frontend/src/pages/Onboarding.tsx, frontend/src/styles/globals.css)
 - 2025-08-26 — Select menu surface made opaque (no bleed-through), added optional `sources` field to onboarding, and updated docs (design + agents) to a minimal playbook. (ref: frontend/src/components/ui/select.tsx, frontend/src/pages/Onboarding.tsx, frontend/design.md, frontend/AGENTS.md)
 - 2025-08-26 — Cadence dropdown made fully opaque (bg-background) and removed onboarding tip copy. (ref: frontend/src/components/ui/select.tsx, frontend/src/pages/Onboarding.tsx)
 - 2025-08-26 — Removed translucent surfaces/backdrop blur from card surfaces and Streams list; unified on fully opaque `card-surface`. (ref: frontend/src/styles/globals.css, frontend/src/pages/Streams.tsx)
- 2025-08-26 — Cadence dropdown raised above navbar (z-index) to avoid line bleed; menu remains fully opaque. (ref: frontend/src/components/ui/select.tsx)
 - 2025-08-26 — Documented overlay layering (opaque surfaces, isolate, high z-index); cleaned Login container to use opaque `card-surface`. (ref: frontend/design.md, frontend/AGENTS.md, frontend/src/pages/Login.tsx)
- 2025-08-26 — Repository setup and contributor guidelines added. (ref: AGENTS.md)
- 2025-08-26 — Frontend scaffolded (Vite + React TS); Login, Onboarding, Streams, StreamView implemented; mock data moved; added frontend AGENTS and basic tests. (ref: frontend/AGENTS.md)
- 2025-08-26 — Restructure: moved frontend to top-level `frontend/`; removed `services/web/*`; updated AGENTS and updates paths. (ref: AGENTS.md, frontend/AGENTS.md)
- 2025-08-26 — Added `frontend/design.md` with critique, principles, and tokens for modernizing UI; linked from `frontend/AGENTS.md`. (ref: frontend/design.md)
- 2025-08-26 — Replaced `frontend/design.md` with Streams v1 design language (role-based tokens, IA, components, guardrails). Added `frontend/src/styles/tokens.css` and `frontend/src/theme.ts` to hydrate tokens. (ref: frontend/design.md)
- 2025-08-26 — Applied modern UI pass: tokens wired, gradients removed, unified radius, rebuilt NavBar and Link Cards (items) with low-ink actions; adjusted layout/typography. (ref: frontend/AGENTS.md)
- 2025-08-26 — Palette update: switched from blue/black cast to warm paper + jade accent (role-based tokens). Updated design doc with neuroscience notes and tone guidance. (ref: frontend/design.md, frontend/src/theme.ts)
- 2025-08-26 — Added Tailwind + shadcn-style setup (tokens mapped to Tailwind, base UI components). Updated design doc with shadcn integration and patterns summary. (ref: frontend/components.json, frontend/tailwind.config.ts, frontend/src/components/ui/*)
- 2025-08-26 — Backend scaffolded (docs-only): created backend folder with AGENTS, SCHEMA, ENVIRONMENT, LLM_ADAPTER, SCHEDULER, TODO; updated README index. (ref: backend/*, README.md)
- 2025-08-26 — Backend FastAPI scaffold: minimal app + health endpoint, env templates (.env.example/.dev/.prod), Supabase client factory, tests; updated backend AGENTS/TODO. (ref: backend/src/app/*, backend/tests/*, .env*)
 - 2025-08-26 — Backend packaging switched to Poetry; added `backend/pyproject.toml`; removed `requirements*.txt`; updated docs with Poetry run instructions; moved env templates into `backend/`. (ref: backend/pyproject.toml, backend/README.md, backend/AGENTS.md, backend/.env*)
 - 2025-08-26 — Added minimal profiles schema and RLS (migration 0001); created Supabase runbook for migrations and verification; trimmed SCHEMA.md to profiles-only. (ref: backend/migrations/2025-08-26_0001_profiles.sql, backend/SUPABASE_RUNBOOK.md, backend/SCHEMA.md)
 - 2025-08-26 — Profiles API: added GET/PUT `/me/profile`, Pydantic models, Supabase repository, and tests; enabled Supabase JWT auth (Authorization Bearer). (ref: backend/src/app/**/*, backend/tests/*)

Template
- YYYY-MM-DD — Short description of what changed and why. (ref: #<issue> / PR <link>)

## Task Board
Track work items using simple checklists. Move items between sections as work progresses.

### Todo
- [ ] Backend: monitor worker logs and metrics in production-like runs; decide on DB-level RPCs for claim/tick with SKIP LOCKED
- [ ] Frontend: add empty-states and loading skeletons — frontend
- [ ] Frontend: item actions placeholders (Save / More-like / Less-like) — frontend
- [ ] Frontend: add e2e smoke (Playwright) — frontend
 - [ ] Frontend: Streams — support link embeds (e.g., YouTube) with improved layout; apply small visual tweaks to current streams — frontend
 - [ ] Backend: decide Python framework and project skeleton — backend
 - [ ] Backend: env loader and config module — backend
 - [ ] Backend: DB client integration (Supabase/Postgres) — backend
 - [x] Backend: implement LLM adapter (function-first, Azure) — backend
 - [ ] Backend: scheduler poller and jobs table migrations — backend

### In Progress
- [ ] Frontend: visual polish pass and accessibility check — branch: feat/frontend-polish
 - [ ] Backend: wire logging strategy and request context — backend
 - [ ] Backend: job system bring-up (enqueue/claim/execute/run) — backend

### Done
- [ ] Frontend: scaffold + core pages — merged in init (local) on 2025-08-26
 - [ ] Backend: scaffold docs and planning — 2025-08-26
 - [ ] Backend: FastAPI app + env templates + Supabase client factory + tests — 2025-08-26

## 2025-08-28 — Backend Search Workflow Refactor
- Implemented ID-first, schema-first search workflow:
  - Added `backend/src/app/llm/search_steps.py` with LLM functions and Pydantic schemas for queries, filtering, follow-ups, and curations.
  - Refactored orchestrator `backend/src/app/agents/search_workflow.py` to use the new steps, assign short link IDs ("01", "02"…), route Exa per `query_type`, read only 2–3 items, and consolidate into curations.
  - Updated tests: replaced mock workflow test to cover ID-based flow; live test now gated by `RUN_LIVE_OPENAI_TESTS=1` and checks `curations`.
  - Updated `backend/AGENTS.md` with the new workflow design and constraints.
  - Centralized prompts with double-braced variables in `backend/src/app/llm/prompts.py`; fixed LLM temperature to 1.0 globally.

- TODO: Improve cost accounting granularity (per step: search vs. contents, round 1 vs. follow-ups) and add token cost aggregation (prompt/completion) to workflow outputs.

### Task Board
- Moved: “Refactor workflow into llm/ with JSON schemas and prompts” → Done.
- Added: Wire stream memory into `additional_context_json` (future runs) → Todo.

Guidelines
- Keep tasks actionable and testable; prefer TDD where feasible.
- Reference the relevant service path (e.g., `services/api/backend/`).
- After completing a task, update this board and the service’s `AGENTS.md`.


## 2025-08-28 — Search Refinements (cost + fidelity)
- Reduced query generation to exactly 5 to lower Exa fanout cost.
- Removed candidate cap: pass all deduped candidates to the LLM for filtering.
- Updated live full‑trace test to print each step’s raw prompts/outputs.
