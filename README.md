# innernets

Monorepo for the InnerNets web product. This README orients new engineers and links to deeper docs.

## Layout
- `frontend/` — Vite + React web app
- `backend/` — FastAPI app, scheduler/worker, agents, tests
- `docs/` — planning and architecture docs

## Start Here
- Architecture overview: `docs/architecture-runs-scheduler.md`
- Integration guide (frontend ↔ backend): `docs/integration.md`
- Changelog & task board: `docs/updates.md`

## Service Docs Index
- Frontend: `frontend/AGENTS.md`, `docs/frontend-design.md`
- Backend: `backend/AGENTS.md`, `backend/README.md`, `docs/backend-environment.md`, `docs/backend-scheduler.md`, `docs/backend-schema.md`, `docs/backend-llm-adapter.md`, `docs/backend-roadmap.md`
- Surfer service (external): `docs/surfer-docker-integration.md`, `docs/surfer-docker-service-api.md`

## Quick Notes
- Auth: Backend verifies Supabase JWT (audience `authenticated`). Frontend sends `Authorization: Bearer <token>`.
- Streams: Creating a Stream also creates a Schedule (per-user cadence). Runs are executed by a worker and persisted as curations (markdown `body_md` + links) that the frontend renders.
- Agents: Surfer is the default agent for Streams. The Exa search-only path remains for legacy/testing.
