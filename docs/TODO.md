# TODO (Post‑Auth/TLS Hardening)

This list tracks deferred items we purposely left for later. Keep entries concise, with file paths where useful. Excludes staging setup tasks.

## Backend — Supabase Client & Resilience
- Improve connection reuse (optional, later): adopt a single shared `httpx.Client` (startup lifespan) for PostgREST, and send per‑request headers `Authorization: Bearer <user_jwt>` + `apikey`. Keep service‑role Supabase client for internal jobs. Rationale: one pool for all users; best TLS/keep‑alive behavior. Files: new wrapper (e.g., `backend/src/app/postgrest_client.py`), adjust repos.
- Unify retry and error mapping across repos: wrap Supabase `.execute()` with one retry on `httpx.ConnectTimeout/ConnectError/ReadError` and map repeat failure to 503 `UpstreamUnavailable`. Extend beyond Streams.
  - backend/src/app/repositories/profile_repo.py — reads/writes for profiles
  - backend/src/app/repositories/urls_repo.py — URL registry operations
  - backend/src/app/repositories/curations_repo.py — latest/runs reads (service role)
- Typed error model: parse PostgREST errors and return `{code,message}` up the stack instead of raw text. Centralize in the wrapper.

## Backend — Scheduler & Finalizer
- Surfer health gate: before submitting/polling jobs, ensure the Surfer service is healthy. On API/worker startup, poll `SURFER_BASE_URL/healthz` with a short backoff until healthy (bounded by a readiness timeout). If unhealthy, short‑circuit dependent endpoints with HTTP 503 instead of attempting requests. Make URL/timeouts configurable (e.g., `SURFER_HEALTH_URL`, `SURFER_HEALTH_TIMEOUT_S`, `SURFER_HEALTH_RETRY_S`) and log health state transitions.
- Standalone finalizer runner: add `backend/src/app/scheduler/finalizer_main.py` to run the finalize loop when using split processes (no in‑app scheduler). Document start/stop and recommended intervals.
- Finalizer enhancements: light backoff/`next_check_at` to avoid rechecking the same run too often; add logging/metrics counters for finalized count, success, and skip reasons. File: `backend/src/app/scheduler/finalizer.py`.
- Deferred from cleanup (post‑staging):
  - Atomic job claiming for concurrent workers (single UPDATE … RETURNING pattern).
  - Metrics/observability (queue depth, latencies, success/fail).

## Frontend — UX & Behavior
- Error UX polish: distinguish 401 (“Session expired. Please sign in again.”) from 5xx/503 (“Temporary connectivity issue. Retrying…”). Files: `frontend/src/lib/api.ts`, `frontend/src/pages/Streams.tsx`, `frontend/src/pages/StreamView.tsx`.
- Visibility‑based polling control: pause “latest” polling when the tab is hidden; do one catch‑up fetch on focus. File: `frontend/src/pages/StreamView.tsx` (or shared polling util).
- Optional SPA auth mitigations: preemptive refresh near expiry and single retry on 401 in the API wrapper to reduce idle hiccups.
- Accessibility pass: ARIA roles on dialogs/menus, focus management, link semantics. File hints: `frontend/src/components/ui/dialog.tsx`, global nav/menu components. Track a11y checklist in `frontend/AGENTS.md`.

## Docs & Tooling
- Hygiene: run `markdownlint` and `prettier` across `docs/**`. Add brief style notes to AGENTS.
- Frontend docs: add troubleshooting section (CORS, missing envs, 401 from backend); confirm and document required Vite envs and sample `.env.local`.
- CI basics: backend pytest, frontend vitest, markdownlint/prettier checks. Optional: mypy/pyright for backend and ESLint for frontend.

## Naming & Consistency
- Standardize field name from `sources_hints` → `sources` across APIs/docs. Keep adapter in code until schema rename; plan migration later.
- Ensure docs use consistent terms: “Stream”, “Run”, “Curation (cluster)”, “URL registry”.

## Security & Secrets
- Re‑audit that no secrets are committed; ensure `.env*` are gitignored and templates contain placeholders only.
- Document basic secret rotation and least‑privilege access for service role keys.

---

Context: We implemented the minimal fix now — cached per‑token Supabase client (reuses HTTP pools) and a one‑shot retry + 503 mapping on Streams reads. The items above are follow‑ups for robustness and polish.
