# Scheduler & Jobs (Design)

Objective
- Provide minimal, reliable scheduling that can scale or be swapped later.
- Start with a DB-driven poller and jobs table. Keep contracts stable.

Model (see SCHEMA.md)
- schedules: user-owned cadence (cron or interval), timezone-aware, active flag.
- jobs: queued work units derived from schedules, with attempts and status.
- runs: execution unit (a job may spawn one run), with metrics and token usage.

Flow (initial)
- Ticker (single process) wakes every `SCHEDULE_POLL_INTERVAL_MS`.
- Select due schedules (active, next_run_at <= now) using `FOR UPDATE SKIP LOCKED`.
- Enqueue jobs for selected schedules, respecting `SCHEDULE_MAX_JOBS_PER_TICK`.
- Executor claims queued jobs and runs the Search Agent loop, writing a `runs` row and results.
- Update schedule.next_run_at using cron/interval calculation.

Concurrency & Idempotency
- Use DB-row locks to prevent multi-claim in concurrent workers.
- Generate deterministic `idempotency_key` for (schedule_id, window) to avoid duplicates.
- Mark jobs terminal states (`succeeded`, `failed`) and cap retries via `max_attempts`.

Retry Policy
- On transient errors: exponential backoff with jitter; increment `attempts`.
- On rate limit (provider): honor `retry_after` if present; else default backoff.
- On permanent errors: mark `failed` with `last_error` and surface actionable codes.

Upgrade Path
- Swap ticker/executor to Celery (Redis) or a managed scheduler; keep tables as the source of truth.
- Consider pg_cron for schedule triggering if available; still funnel into `jobs` to centralize execution.

Observability
- Structured logs per job/run with trace IDs.
- Metrics: queue depth, latency (schedule to start), success rate, retry rate.

Security
- Run workers with least-privilege DB access.
- Avoid embedding secrets in job payloads; resolve secrets at execution time.

Change Log
- 2025-08-26 — Initial DB-driven scheduler and worker design.
