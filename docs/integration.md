# Integration — Frontend ↔ Backend

Scope: How the web app talks to the backend, how Streams are persisted and run, and which endpoints are used. This reflects the current implementation (Surfer as default agent) and points to detailed specs.

## Goals
- Frontend uses backend APIs with Supabase JWTs (Bearer) for user‑scoped operations.
- Persist user Streams and their runs (curations are stored and served via API).
- De‑duplicate and track URLs via a URL registry.
- Keep contracts typed and RLS‑safe.

## Current State

Backend
- FastAPI app: `backend/src/app/main.py` (`/healthz`, `/`, routers under `/me` and `/streams`).
- Auth: Supabase JWT verification in `backend/src/app/auth.py` (Bearer, audience `authenticated`).
- Supabase clients: service‑role and user‑scoped (`backend/src/app/supabase_client.py`).
- Scheduler & worker: `backend/src/app/scheduler/*` (ticker, jobs, worker loop). Schedules are created per Stream.
- Agents: Surfer workflow is default (`backend/src/app/agents/surfer_workflow.py`); legacy search‑only retained (`search_workflow.py`). Dispatcher selects agent per job (`dispatcher.py`).
- Persistence: Streams, URL registry, and curations (runs, clusters, links) implemented with RLS. See `backend/migrations/*` and `docs/backend-schema.md`.

Frontend
- Pages: `Login`, `SignUp`, `Onboarding`, `Streams`, `StreamView` (see `frontend/src/pages/*`).
- API wrapper: `frontend/src/lib/api.ts` injects `Authorization: Bearer <token>`.
- Streams: live API integration for create, list, edit/delete, run‑now, and run feed.

## APIs Used by the Frontend
- `POST /streams` → create a Stream (creates its schedule under the hood).
- `GET /streams` → list user streams (active only); includes `latest_run_at` when available.
- `GET /streams/{id}` → get a single Stream.
- `PUT /streams/{id}` → update `mission`, `sources` (stored as `sources_hints`), `cadence`, `time_zone`, `active`.
- `DELETE /streams/{id}` → soft‑delete by default (disables schedule); `?hard=true` for full delete.
- `POST /streams/{id}/run` → enqueue a job immediately (Run Now).
- `GET /streams/{id}/latest` → latest run with `curations`.
- `GET /streams/{id}/runs?limit=10&before=<iso>` → paginated runs feed for infinite scroll.

### Request/Response Examples (Streams)

- POST `/streams`
  - Request
    - Headers: `Authorization: Bearer <token>`
    - Body
      - `{ "mission": "AI news for founders", "sources": "arXiv, Hacker News", "cadence": "weekly", "time_zone": "UTC" }`
  - Response 201
    - `{ "id": "s-123", "mission": "AI news for founders", "sources": "arXiv, Hacker News", "cadence": "weekly", "time_zone": "UTC", "active": true, "created_at": "...", "updated_at": "..." }`

- GET `/streams`
  - Response 200
    - `[{ "id": "s-123", "mission": "AI news for founders", "sources": "arXiv, Hacker News", "cadence": "weekly", "time_zone": "UTC", "active": true, "latest_run_at": "2025-01-01T00:00:00Z" }]`

- GET `/streams/{id}`
  - Response 200
    - `{ "id": "s-123", "mission": "AI news for founders", "sources": "arXiv, Hacker News", "cadence": "weekly", "time_zone": "UTC", "active": true }`

- PUT `/streams/{id}`
  - Request: `{ "mission": "AI ops digest", "cadence": "3xweek" }`
  - Response 200: same shape as GET `/streams/{id}`

- POST `/streams/{id}/run`
  - Response 202: `{ "job_id": "j-abc", "status": "queued" }`

- GET `/streams/{id}/latest`
  - Response 200
    - `{ "run_id": "r-1", "started_at": "2025-01-01T00:00:00Z", "finished_at": "2025-01-01T00:10:00Z", "curations": [ { "title": "OpenAI system paper", "body_md": "...markdown...", "links": [ { "url": "https://example.com/a", "title": "A", "domain": "example.com", "position": 0 } ], "position": 0, "hook": "..." } ] }`

- GET `/streams/{id}/runs?limit=10&before=<iso>`
  - Response 200
    - `{ "runs": [ { "id": "r-2", "run_at": "2025-01-02T00:00:00Z", "started_at": "2025-01-02T00:00:00Z", "finished_at": "2025-01-02T00:06:00Z", "curations": [ { "title": "...", "body_md": "...", "links": [ { "url": "https://...", "domain": "...", "title": "...", "position": 0 } ], "position": 0 } ] } ], "next_cursor": "2025-01-01T00:00:00Z" }`

Notes
- All endpoints require `Authorization: Bearer <supabase_access_token>`.
- CORS origin defaults to `http://localhost:5173` and can be adjusted via `CORS_ALLOW_ORIGINS`.

### Error Model
- Shape
  - `{ "code": string, "message": string }`
- Status codes
  - 400/422 → `code: "BadRequest"`
  - 401 → `code: "Unauthorized"`
  - 403 → `code: "Forbidden"`
  - 404 → `code: "NotFound"`
  - 409 → `code: "Conflict"`
  - 429 → `code: "RateLimited"`
  - 5xx → `code: "Internal"`
- Examples
  - 422 invalid body: `{ "code": "BadRequest", "message": "Validation failed" }`
  - 404 not found: `{ "code": "NotFound", "message": "Stream not found" }`

## Auth
- Dev flow: obtain a Supabase access token (via SignUp/Login pages or the dev token script) and store it client‑side. The API receives the token in the `Authorization` header.
- Backend verifies tokens with `SUPABASE_JWT_SECRET` and enforces audience `authenticated` (configurable).

Notes (SPA idle behavior)
- The frontend uses `@supabase/supabase-js` with session persistence and auto refresh. After long idles, backgrounded tabs, or device sleep, browsers may throttle timers; the first request after resume can briefly 401 if the access token expired and the refresh hasn’t completed yet. Subsequent requests succeed once the library refreshes the session.
- Mitigations (optional): trigger a session check on `visibilitychange` or retry once on 401. Alternative architecture: move to a backend-managed cookie session (BFF) to eliminate transient 401s.

## Data Flow (High Level)
1. User creates a Stream from Onboarding (`mission`, optional `sources`, `cadence`).
2. Backend stores the Stream and creates a user‑owned Schedule with `meta.stream_id` and `meta.agent='surfer_v1'`.
3. The scheduler enqueues jobs when schedules are due; Run Now creates an ad‑hoc job immediately.
4. Worker claims the job, dispatcher selects the agent (Surfer by default), results are remixed into curations and persisted.
5. Frontend fetches the latest or historical runs and renders markdown bodies (`body_md`) and link chips.

## Local Development
- Backend environment and secrets: `docs/backend-environment.md`. Create `backend/.env` based on the examples.
- Surfer service: `docs/surfer-docker-integration.md` (Docker instructions); API contract in `docs/surfer-docker-service-api.md`.
- Dev token: use `backend/supa_mint_test_token.sh` to mint a test Supabase user token for local development (see backend README/ENV docs for usage).

## References
- Architecture: `docs/architecture-runs-scheduler.md`
- Schema overview: `docs/backend-schema.md` and SQL in `backend/migrations/`
- Scheduler design: `docs/backend-scheduler.md`
- Backend env: `docs/backend-environment.md`
- Surfer integration: `docs/surfer-docker-integration.md`, `docs/surfer-docker-service-api.md`
