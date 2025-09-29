# Project Updates and Tasks

Use this document to record natural-language updates and maintain a lightweight task board. Keep entries concise, dated, and linked to issues/PRs where possible.

## Updates Log
- 2025-09-29 — Local Docker test verified: converted playbook steps to checkbox tasks and marked the Local Docker Test section as Done after successful verification.
- 2025-09-29 — Staging/Dev/Prod Playbook: added `docs/staging-dev-prod-playbook.md` outlining environments, branching, CI/CD, Azure VM setup, DNS/TLS, Supabase plan, and open decisions to finalize before wiring CI. Linked to Surfer and backend runbooks.
- 2025-09-29 — Staging infra files: added `backend/Dockerfile`, `backend/.dockerignore`, root `compose.staging.yml`, and GitHub Action `.github/workflows/deploy-staging.yml` for SSH-based deploys to the Azure VM.
- 2025-09-29 — Staging checklist & env example: added detailed bring-up checklist to `docs/staging-dev-prod-playbook.md` and `backend/.env.example.staging` for VM setup.
- 2025-09-29 — Frontend Docs & Consistency: aligned `sources` naming in StreamView (removed `sources_hints` usage); added Troubleshooting and optional dev proxy guidance to `frontend/README.md`; added `frontend/.env.example`; surfaced an a11y checklist in `frontend/AGENTS.md`; standardized test file naming to `test_*` and simplified Vitest include; removed duplicate Vite configs and untracked `*.tsbuildinfo` with `.gitignore`.
- 2025-09-28 — Backend Supabase hardening (minimal): cached per‑token Supabase client to reuse HTTP pools and reduce TLS/EOF hiccups after idle; added a one‑shot retry on Streams reads and mapped repeated failures to HTTP 503. Also created `docs/TODO.md` to track deferred improvements (shared httpx PostgREST client, broader retry mapping, finalizer runner, a11y, CI). (ref: backend/src/app/supabase_client.py, backend/src/app/repositories/streams_repo.py, backend/src/app/routes/streams.py, docs/TODO.md)
- 2025-09-27 — Streams & Runs UX: removed inline "job in queue" status. "Run Now" now disables on enqueue and remains disabled while a run is pending/in‑progress; it re‑enables when `/streams/:id/latest` reports a newer finished run. Added hover tooltip on the disabled button; no new inline text. Also added tests for run gating and pagination overfetch guard. (ref: frontend/src/pages/StreamView.tsx, frontend/src/test/test_stream_run_gating.tsx, frontend/src/test/test_streamview_pagination.tsx)
- 2025-09-27 — Frontend auth tests: added Vitest + RTL tests for session gating, login/sign-up flows (including confirmation-required path), and error banners on Streams/StreamView. Updated Vitest config and JSDOM setup. (ref: frontend/src/test/*)
- 2025-09-28 — Scheduler Finalizer: implemented submit+finalize pattern for Surfer runs. We now record `surfer_job_id` immediately on submit and added a background finalizer that reconciles late completions (e.g., laptop sleep or long jobs). Finalizer fetches results from Surfer and persists curations, then marks runs/jobs succeeded. Keeps existing wait logic; timeouts are no longer terminal. (ref: backend/src/app/agents/surfer_workflow.py, backend/src/app/scheduler/{finalizer.py,runner.py,jobs.py})
- 2025-09-27 — Document SPA idle auth behavior: noted that after long idle/background tabs, the first request may 401 until supabase-js refreshes the session; listed mitigation options and BFF alternative. (ref: frontend/README.md, docs/integration.md, frontend/AGENTS.md)
- 2025-09-27 — Frontend auth refactor: switched to `@supabase/supabase-js` for session management. Replaced manual password grant and localStorage token handling with a session-backed `AuthProvider`; Login/SignUp now use `signInWithPassword`/`signUp` and handle the confirmation-required path. API wrapper (`src/lib/api.ts`) attaches `Authorization` from the current session. Streams/StreamView show minimal 401/5xx banners; removed dev/mock fallbacks to keep behavior standard.
- 2025-09-27 — API contracts (Streams) and healthz: added lightweight Pydantic response models to Streams endpoints and basic cadence validation (`daily|3xweek|weekly|discovery`), plus bounded `limit` on runs. `/healthz` now reports `surfer_ok` by probing `${SURFER_BASE_URL}/healthz` with a short timeout. (ref: backend/src/app/routes/streams.py, backend/src/app/main.py, docs/cleanup.md)
- 2025-09-27 — Docs consolidation: moved service docs from `backend/` and `frontend/` into `docs/` and updated all cross-links. New files: `docs/backend-environment.md`, `docs/backend-scheduler.md`, `docs/backend-schema.md`, `docs/backend-llm-adapter.md`, `docs/backend-exa-usage.md`, `docs/backend-supabase-runbook.md`, `docs/backend-roadmap.md`, and `docs/frontend-design.md`. Removed duplicates from `backend/` and `frontend/`. Updated indexes in `README.md`, `backend/README.md`, and `backend/AGENTS.md`.
- 2025-09-27 — Staging worker setup: disabled in‑app scheduler in Procfile (switch web to uvicorn) and run a single dedicated worker process. Added run idempotency (unique on `runs.job_id` + idempotent `start_run`), minimal console logs, worker SIGTERM handling, and documented Surfer timeout defaults. (ref: backend/Procfile, backend/src/app/scheduler/{jobs.py,worker.py,worker_main.py}, backend/migrations/2025-09-27_0005_runs_job_id_unique.sql, docs/backend-environment.md, docs/cleanup.md)
- 2025-09-27 — Surfer integration tests: added dispatcher routing tests and Surfer client polling/timeout/409 tests; added Surfer health curl to env docs. (ref: backend/tests/test_dispatcher.py, backend/tests/test_surfer_client.py, docs/backend-environment.md, docs/cleanup.md)
- 2025-09-26 — Repo cleanup plan drafted: added `docs/cleanup.md` covering docs consolidation (mark search-only docs as legacy), missing env templates, scheduler/worker hardening, Surfer dispatcher/tests, OpenAI provider support, API contract typing, and frontend auth/UX polish. Pending approval to execute.
- 2025-09-25 — Auth UX hardening: Login/SignUp now surface Supabase error messages (e.g., invalid credentials, email not confirmed) and stop falling back to mock auth when Supabase env vars are present. This prevents navigating without a JWT and spamming the backend with 401s on `/streams*`. (ref: frontend/src/pages/Login.tsx, frontend/src/pages/SignUp.tsx)
- 2025-08-29 — Fixed external link clicks on Stream page by removing JS `window.open` handlers and container-level `onClick`. Links now rely on native anchor behavior with `target="_blank"` + `rel="noopener noreferrer"`, ensuring consistent new-tab opening across browsers and blockers. (ref: frontend/src/components/ItemCard.tsx)
- 2025-08-29 — Hardened StreamView link normalization: accept `url|href|link`, add `https://` for `www.` or schemeless links, and expose a dev debug flag `window.__IN_DEBUG_LINKS = true` to log raw vs normalized links. Also add data attributes to ItemCard for quick DOM inspection. (ref: frontend/src/pages/StreamView.tsx, frontend/src/components/ItemCard.tsx)
- 2025-08-29 — Backend: fix for missing links in `GET /streams/:id/runs` — clusters were grouped before links were attached, so API returned empty `links`. Now links are joined via explicit FK `urls:urls!curation_cluster_links_url_id_fkey(...)` and attached prior to grouping. Removed metrics-based fallback to keep a single source of truth. (ref: backend/src/app/repositories/curations_repo.py)
- 2025-08-29 — Backend: normalize LLM `link_ids` (accepts forms like "1", "01", "#01") when persisting curations so they map to assigned IDs ("01"). (ref: backend/src/app/agents/search_workflow.py)
- 2025-08-29 — Added reverse‑chronological runs feed: backend supports `GET /streams/:id/runs?limit=10&before=<iso>` (returns runs with clusters+links and `next_cursor`), and frontend StreamView renders a minimal feed with Load more and intersection‑based infinite scroll. (ref: backend/src/app/repositories/curations_repo.py, backend/src/app/routes/streams.py, frontend/src/pages/StreamView.tsx)
- 2025-08-29 — Streams UX polish: added loader skeletons to Streams list to avoid empty flash and removed stray divider when list is empty. Adjusted auth flows: Login now routes to Streams; added Sign up page that routes to Onboarding (Create Stream). Onboarding no longer pre-fills from previous local values. (ref: frontend/src/pages/Streams.tsx, frontend/src/pages/Login.tsx, frontend/src/pages/SignUp.tsx, frontend/src/App.tsx, frontend/src/components/NavBar.tsx, frontend/src/pages/Onboarding.tsx)
- 2025-08-29 — Scheduler hardening: map cadence labels ('daily'/'3xweek'/'weekly'/'discovery') to real intervals; auto-disable the demo schedule named 'e2e-scheduler-demo'; and skip agent execution for jobs without `stream_id` whose params only have `schedule_id` (prevents wasteful demo runs). (ref: backend/src/app/scheduler/ticker.py, backend/src/app/agents/search_workflow.py)
- 2025-08-29 — Removed demo script that created 'e2e-scheduler-demo' schedules and cleaned docs. New sign-ups only create per-stream schedules; no demo schedules are created. (ref: backend/src/app/scheduler/demo.py removed, docs/backend-scheduler.md, docs/backend-environment.md, backend/AGENTS.md)
- 2025-08-29 — Streams edit/delete: added PUT `/streams/:id` (accepts `mission`, `sources`, `cadence`) and DELETE `/streams/:id` (soft-delete + disable schedule). Frontend StreamView now has Edit and Delete actions with a minimal inline form. Renamed UI copy to “Sources” (was “hints”). Added backend tests for update/delete. (ref: backend/src/app/routes/streams.py, backend/src/app/repositories/streams_repo.py, backend/tests/test_streams_api.py, frontend/src/pages/StreamView.tsx)
- 2025-08-29 — Frontend buttons: added consistent hover effects (lift + shadow + color) across all `Button` variants and the custom `Select` trigger; added a `destructive` button variant for Delete actions. (ref: frontend/src/components/ui/button.tsx, frontend/src/components/ui/select.tsx)
- 2025-08-29 — Delete UX: after confirming delete, StreamView navigates to Streams and shows a one-off success toast; edit modal closes automatically. (ref: frontend/src/pages/StreamView.tsx, frontend/src/pages/Streams.tsx)
- 2025-08-29 — Streams + URL registry + curations storage implemented; Streams API added (create/list/get/update/run-now/latest). Orchestrator persists runs and maps link IDs to URL registry. Frontend integrated with API: login via Supabase password grant, create streams, list streams, view latest curations, and trigger Run Now. CORS enabled for dev. (ref: backend migrations 0003; backend/src/app/routes/streams.py; backend/src/app/agents/search_workflow.py; frontend src/pages/Login/Onboarding/Streams/StreamView)
- 2025-08-28 — Scheduler runtime integrated: added in-app background scheduler (thread) and standalone worker entrypoint; one-command launcher (`app.run_backend`) and Procfile provided. Ticker hardened with due-filter guard and scheduled payload now hydrated from schedule meta params. Enhanced demo to stress queue and print per-job outputs. (ref: backend/src/app/main.py, backend/src/app/scheduler/{runner.py,worker_main.py,ticker.py,demo.py}, backend/src/app/run_backend.py, backend/Procfile)
- 2025-08-28 — Fixed structured outputs for search workflow: enforced integer 0–100 scoring via prompt update and Pydantic validator (coercion from 0–5 floats). Tightened Azure provider system hint to avoid decimals for integer fields. Added unit test for score coercion. (ref: backend/src/app/llm/schemas.py, backend/src/app/llm/prompts.py, backend/src/app/llm/providers/azure_openai.py, backend/tests/test_llm_schema_coercion.py, backend/src/app/agents/search_workflow.py)
- 2025-08-27 — Refined Exa integration: removed public `/exa/*` routes; workers call `exa-py` directly via `ExaClient`. Updated docs and tests accordingly. (ref: backend/src/app/clients/exa_client.py, docs/backend-exa-usage.md)
- 2025-08-27 — Backend LLM adapter implemented (function-first, Azure); added tool registry, unit tests with mocked HTTP, and updated backend docs/env templates. (ref: backend/src/app/llm/*, backend/tests/test_llm_adapter.py, docs/backend-llm-adapter.md, docs/backend-environment.md)
- 2025-08-27 — Scheduler groundwork: added DB schema (schedules, jobs, runs), env hook for dev test user token, and worker/agent stubs to execute jobs. (ref: backend/migrations/2025-08-27_0002_scheduler.sql, backend/src/app/scheduler/*, backend/src/app/agents/search_workflow.py, docs/backend-scheduler.md, docs/backend-environment.md, docs/backend-roadmap.md)
- 2025-08-26 — Refactored Onboarding and missing-state views to shadcn/Tailwind styles; removed legacy class usage causing “old UI”. (ref: frontend/src/pages/Onboarding.tsx, frontend/src/pages/StreamView.tsx)
- 2025-08-26 — Added token-styled Select component and replaced native select for cadence; removed unused CSS/components; aligned Tailwind v4 import; deleted duplicate Tailwind config. (ref: frontend/src/components/ui/select.tsx, frontend/src/pages/Onboarding.tsx, frontend/src/styles/globals.css)
 - 2025-08-26 — Select menu surface made opaque (no bleed-through), added optional `sources` field to onboarding, and updated docs (design + agents) to a minimal playbook. (ref: frontend/src/components/ui/select.tsx, frontend/src/pages/Onboarding.tsx, docs/frontend-design.md, frontend/AGENTS.md)
 - 2025-08-26 — Cadence dropdown made fully opaque (bg-background) and removed onboarding tip copy. (ref: frontend/src/components/ui/select.tsx, frontend/src/pages/Onboarding.tsx)
 - 2025-08-26 — Removed translucent surfaces/backdrop blur from card surfaces and Streams list; unified on fully opaque `card-surface`. (ref: frontend/src/styles/globals.css, frontend/src/pages/Streams.tsx)
- 2025-08-26 — Cadence dropdown raised above navbar (z-index) to avoid line bleed; menu remains fully opaque. (ref: frontend/src/components/ui/select.tsx)
 - 2025-08-26 — Documented overlay layering (opaque surfaces, isolate, high z-index); cleaned Login container to use opaque `card-surface`. (ref: docs/frontend-design.md, frontend/AGENTS.md, frontend/src/pages/Login.tsx)
- 2025-08-26 — Repository setup and contributor guidelines added. (ref: AGENTS.md)
- 2025-08-26 — Frontend scaffolded (Vite + React TS); Login, Onboarding, Streams, StreamView implemented; mock data moved; added frontend AGENTS and basic tests. (ref: frontend/AGENTS.md)
- 2025-08-26 — Restructure: moved frontend to top-level `frontend/`; removed `services/web/*`; updated AGENTS and updates paths. (ref: AGENTS.md, frontend/AGENTS.md)
- 2025-08-26 — Added `frontend/design.md` with critique, principles, and tokens for modernizing UI; linked from `frontend/AGENTS.md`. (ref: docs/frontend-design.md)
- 2025-08-26 — Replaced `frontend/design.md` with Streams v1 design language (role-based tokens, IA, components, guardrails). Added `frontend/src/styles/tokens.css` and `frontend/src/theme.ts` to hydrate tokens. (ref: docs/frontend-design.md)
- 2025-08-26 — Applied modern UI pass: tokens wired, gradients removed, unified radius, rebuilt NavBar and Link Cards (items) with low-ink actions; adjusted layout/typography. (ref: frontend/AGENTS.md)
- 2025-08-26 — Palette update: switched from blue/black cast to warm paper + jade accent (role-based tokens). Updated design doc with neuroscience notes and tone guidance. (ref: docs/frontend-design.md, frontend/src/theme.ts)
- 2025-08-26 — Added Tailwind + shadcn-style setup (tokens mapped to Tailwind, base UI components). Updated design doc with shadcn integration and patterns summary. (ref: frontend/components.json, frontend/tailwind.config.ts, frontend/src/components/ui/*)
- 2025-08-26 — Backend scaffolded (docs-only): created backend folder with AGENTS, SCHEMA, ENVIRONMENT, LLM_ADAPTER, SCHEDULER, TODO; updated README index. (ref: backend/*, README.md)
- 2025-08-26 — Backend FastAPI scaffold: minimal app + health endpoint, env templates (.env.example/.dev/.prod), Supabase client factory, tests; updated backend AGENTS/TODO. (ref: backend/src/app/*, backend/tests/*, .env*)
 - 2025-08-26 — Backend packaging switched to Poetry; added `backend/pyproject.toml`; removed `requirements*.txt`; updated docs with Poetry run instructions; moved env templates into `backend/`. (ref: backend/pyproject.toml, backend/README.md, backend/AGENTS.md, backend/.env*)
- 2025-08-26 — Added minimal profiles schema and RLS (migration 0001); created Supabase runbook for migrations and verification; trimmed SCHEMA.md to profiles-only. (ref: backend/migrations/2025-08-26_0001_profiles.sql, docs/backend-supabase-runbook.md, docs/backend-schema.md)
 - 2025-08-26 — Profiles API: added GET/PUT `/me/profile`, Pydantic models, Supabase repository, and tests; enabled Supabase JWT auth (Authorization Bearer). (ref: backend/src/app/**/*, backend/tests/*)

## Task Board

### Todo
- [ ] Vercel: connect repo, map `staging.innernets.ai` to `main` deploys, set env vars.
- [ ] Azure VM: install Docker/Compose, clone repo to `/opt/innernets`, add `backend/.env.staging`.
- [ ] Reverse proxy: Nginx/Caddy for `api-staging.innernets.ai` → `127.0.0.1:8000` with HTTPS.
- [ ] Surfer: run separately on VM, private on `8001`; verify `/healthz`.
- [ ] Add `compose.staging.yml` at repo root (build backend locally; extra_hosts host-gateway); do not commit secrets.
- [ ] Minimal GitHub Action: SSH to VM on push to `main`, run `git pull` + `docker compose up -d --build`.
- [ ] Add `.env.example.staging` notes for backend (variables only, no secrets).
- [ ] TODO: choose a container registry (GHCR/ACR) later.

### In Progress
- [ ] Trimmed playbook agreed; awaiting confirmation to add compose + CI skeletons.

### Done
- [x] Author staging/dev/prod playbook and simplify per decisions (subdomain, Surfer private, build on VM).

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
## Task Board

### Todo
- Add small “copy link” affordance next to each curation title (optional for constrained webviews).
- Add backend tests for `/streams/:id/runs` join behavior (ensures `links` always populated).

### In Progress
- None

### Done
- Fix StreamView curations not clickable: ensure `GET /streams/:id/runs` returns `clusters[].links` via explicit FK join and attach before grouping; frontend renders native anchors only.
- Frontend docs & config cleanup: Troubleshooting (CORS/401/missing envs), `.env.example`, a11y checklist in `frontend/AGENTS.md`, test naming standardized, and Vite/tsbuildinfo cleanup.

## 2025-09-25 — Surfer Docker Integration (streams default)
- Added Surfer client and workflow to replace Exa-based search for Streams by default (legacy kept for back-compat).
- New modules: `backend/src/app/clients/surfer_client.py`, `backend/src/app/agents/surfer_workflow.py`, `backend/src/app/agents/dispatcher.py`, `backend/src/app/llm/surfer_steps.py` and prompts.
- Scheduler now uses `schedules.meta.agent` to decide which agent to enqueue; Streams creation sets `meta.agent="surfer_v1"`.
- Worker dispatcher runs Surfer by default; long-running jobs poll every `SURFER_POLL_INTERVAL_S`.
- Env: added `SURFER_*` variables in `backend/.env.example` and `docs/backend-environment.md`.
- Second-stage LLM remix now combines Surfer `{summary,links[]}` into 2–5 highlight curations with richer hooks and explicit link lists.

### Todo
- Add unit tests for dispatcher selection and Surfer client error handling.
- Add API endpoint to expose Surfer job status/log URLs per run for debugging (optional).

## 2025-09-25 — Remix Upgrade (Markdown bodies)
- Planner prompt now returns both `instruction` and `context` (task-first, XML-tagged) for the Surfer agent.
- Remixer prompt redesigned (task-first, XML-tagged) to produce rich markdown bodies (`body_md`) and explicit links; quantity unconstrained.
- Added DB column `curation_clusters.body_md` (migration 0004) and updated API responses to include `body_md`.
- Frontend renders markdown via `react-markdown` and shows links as chips.
