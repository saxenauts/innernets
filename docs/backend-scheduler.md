# Scheduler & Jobs (Design)

See also: `docs/architecture-runs-scheduler.md` for the end‑to‑end picture from Stream creation to run persistence and frontend consumption. The default agent for Streams is `surfer_v1`; the Exa search‑only path is retained for legacy/testing.

Objective
- Provide minimal, reliable scheduling that can scale or be swapped later.
- Start with a DB-driven poller and jobs table. Keep contracts stable.

Model (see backend migrations)
- schedules: user-owned cadence (cron or interval), timezone-aware, active flag.
- jobs: queued work units derived from schedules, with attempts and status.
- runs: execution unit (a job may spawn one run), with metrics and token usage.

Flow (initial)
- Ticker (single process) wakes every `SCHEDULE_POLL_INTERVAL_MS`.
- Select due schedules (active, next_run_at <= now) using `FOR UPDATE SKIP LOCKED`.
- Enqueue jobs for selected schedules, respecting `SCHEDULE_MAX_JOBS_PER_TICK`.
- Executor claims queued jobs and runs the agent workflow, writing a `runs` row and results.
- Update schedule.next_run_at using cron/interval calculation.

Usage (dev)
- Create scheduler tables via migration 0002 (see `backend/migrations/2025-08-27_0002_scheduler.sql`).
- Set `DEV_TEST_USER_TOKEN` in `backend/.env` to a Supabase access token for a test user.
- The dev worker (`app.scheduler.worker.dev_loop`) will:
  - call `ticker.tick()` to enqueue due work from `schedules`
  - call `worker.run_once(handle_job)` to claim one job and execute the workflow

Runtime Modes
- Single command (API + background scheduler): `poetry run python -m app.run_backend` (sets `SCHEDULER_IN_APP=1`).
- Split processes:
  - API: `poetry run uvicorn app.main:app --reload`
  - Worker: `poetry run python -m app.scheduler.worker_main`
  - Optional ticker-only loop is not necessary; the worker loop invokes `tick()` each iteration by default.

Contracts
- Job payload: `{ "agent": "search_only_v1"|"surfer_v1", "params": { ... }, "schedule_id"?: uuid }`
- Run metrics: `{ "queries": int, "reads": int, "cost_exa": number, "usage_tokens": {"prompt": int, "completion": int, "total": int } }`

Minimal Interfaces
- `jobs.enqueue(user_id, payload, schedule_id?, idempotency_key?)` → job row (upsert on idempotency_key)
- `ticker.tick()` → enqueues jobs for due schedules and advances `next_run_at`
- `jobs.claim(max=1)` → list[job] oldest queued
- `jobs.mark_running(job_id)`; `jobs.mark_done(job_id, success|failed, error?)`
- `runs.start(job_id)` → run row; `runs.finish(run_id, status, metrics?, error?)`

Workflow vs. Loop
- Each job executes a deterministic, acyclic workflow. Steps run serially; outputs flow into the next step.

Concurrency & Idempotency
- Use DB-row locks to prevent multi-claim in concurrent workers.
- Generate deterministic `idempotency_key` for (schedule_id, window) to avoid duplicates.
- Mark jobs terminal states (`succeeded`, `failed`) and cap retries via `max_attempts`.

Retry Policy
- On transient errors: exponential backoff with jitter; increment `attempts`.
- On rate limit (provider): honor `retry_after` if present; else default backoff.
- On permanent errors: mark `failed` with `last_error` and surface actionable codes.

Observability
- Structured logs per job/run with trace IDs.
- Metrics: queue depth, latency (schedule to start), success rate, retry rate.

Security
- Run workers with least-privilege DB access.
- Avoid embedding secrets in job payloads; resolve secrets at execution time.

Change Log
- 2025-08-26 — Initial DB-driven scheduler and worker design.

## Demo Note

The previous E2E demo script that created a schedule named `e2e-scheduler-demo` has been removed. The ticker proactively disables any schedule with that exact name if found. Use real Streams and schedules for testing. For ad‑hoc tests, enqueue jobs directly via the API or by inserting into `jobs` with clear metadata.

