# Project Updates and Tasks

Use this document to record natural-language updates and maintain a lightweight task board. Keep entries concise, dated, and linked to issues/PRs where possible.

## Updates Log
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
- [ ] Frontend: add empty-states and loading skeletons — frontend
- [ ] Frontend: item actions placeholders (Save / More-like / Less-like) — frontend
- [ ] Frontend: add e2e smoke (Playwright) — frontend
 - [ ] Frontend: Streams — support link embeds (e.g., YouTube) with improved layout; apply small visual tweaks to current streams — frontend
 - [ ] Backend: decide Python framework and project skeleton — backend
 - [ ] Backend: env loader and config module — backend
 - [ ] Backend: DB client integration (Supabase/Postgres) — backend
 - [ ] Backend: implement LLM adapter (baseline chat) — backend
 - [ ] Backend: scheduler poller and jobs table migrations — backend

### In Progress
- [ ] Frontend: visual polish pass and accessibility check — branch: feat/frontend-polish
 - [ ] Backend: wire logging strategy and request context — backend

### Done
- [ ] Frontend: scaffold + core pages — merged in init (local) on 2025-08-26
 - [ ] Backend: scaffold docs and planning — 2025-08-26
 - [ ] Backend: FastAPI app + env templates + Supabase client factory + tests — 2025-08-26

Guidelines
- Keep tasks actionable and testable; prefer TDD where feasible.
- Reference the relevant service path (e.g., `services/api/backend/`).
- After completing a task, update this board and the service’s `AGENTS.md`.
