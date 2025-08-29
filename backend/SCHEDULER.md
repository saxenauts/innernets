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

Usage (dev)
- Create scheduler tables via migration 0002 (see `backend/migrations/2025-08-27_0002_scheduler.sql`).
- Set `DEV_TEST_USER_TOKEN` in `backend/.env` to a Supabase access token for a test user.
- The dev worker (`app.scheduler.worker.dev_loop`) will:
  - call `ticker.tick()` to enqueue due work from `schedules`
  - call `worker.run_once(handle_job)` to claim one job and execute the workflow
- For now, Exa calls can be mocked in tests; when ready, set `EXA_API_KEY` and call `agents.search_workflow.run`.

Runtime Modes
- Single command (API + background scheduler): `poetry run python -m app.run_backend` (sets `SCHEDULER_IN_APP=1`).
- Split processes:
  - API: `poetry run uvicorn app.main:app --reload`
  - Worker: `poetry run python -m app.scheduler.worker_main`
  - Optional ticker-only loop is not necessary; the worker loop invokes `tick()` each iteration by default.

Contracts
- Job payload: `{ "agent": "search_only_v1", "params": { "mission": string, "sources": string[]?, "hints": object?, "schedule_id"?: uuid } }`
- Run metrics: `{ "queries": int, "reads": int, "cost_exa": number, "usage_tokens": {"prompt": int, "completion": int, "total": int } }`

Minimal Interfaces
- `jobs.enqueue(user_id, payload, schedule_id?, idempotency_key?)` → job row (upsert on idempotency_key)
- `ticker.tick()` → enqueues jobs for due schedules and advances `next_run_at`
- `jobs.claim(max=1)` → list[job] oldest queued
- `jobs.mark_running(job_id)`; `jobs.mark_done(job_id, success|failed, error?)`
- `runs.start(job_id)` → run row; `runs.finish(run_id, status, metrics?, error?)`

Workflow vs. Loop
- Each job executes a deterministic, acyclic workflow for the search agent:
  1) Generate 5 search queries (LLM)
  2) Exa search per query (25 results), dedupe, assign IDs
  3) Filter candidates to read (LLM) — pass all deduped candidates (IDs only), select 2–3
  4) Exa contents for selected IDs; compact summaries
  5) Propose 3–6 follow‑up queries (LLM)
  6) Exa search for follow‑ups (continue ID numbering)
  7) Consolidate curations (LLM) with titles, hooks, 3–4 link_ids each
- Steps run serially; outputs flow into the next step. Prompt/schema changes are isolated in `llm/search_steps.py` and `llm/prompts.py`. The orchestrator enforces IDs‑only to the LLM and maintains the ID↔URL mapping.

Call Graph (dev)
- `worker.dev_loop()`
  - `ticker.tick()` → enqueues jobs (idempotent per minute window)
  - `worker.run_once(handle_job)`
    - `jobs.claim(limit=1)` → `jobs.start_run(job_id)`
    - `handle_job(job)` → `agents.search_workflow.run(job, user_token)`
    - `runs.finish(run_id, status, metrics)` → `jobs.mark_done(job_id, success)`

Dev Worker vs Production
- Dev Worker (`dev_loop`):
  - Purpose: local bring-up to exercise the full path (enqueue → claim → execute workflow → record metrics) without running the HTTP API or front‑end.
  - Uses: service-role access for scheduler tables (schedules/jobs/runs). This bypasses RLS by design and is safe server-side.
  - Optional `DEV_TEST_USER_TOKEN`: used only if the job’s workflow needs to access RLS-protected, user-owned tables (e.g., future per-user artifacts). For Exa and LLM calls we use server-side provider keys, so the token is not required today.
  - Scope: single process can process jobs across all users; not per-user. It is a convenience loop for development.
- Production Worker(s):
  - One or more processes/containers running the same executor logic. Ticker may run in one instance; executor can be horizontally scaled.
  - DB Access:
    - Scheduler tables (schedules/jobs/runs): service role client (bypasses RLS) with least-privilege role.
    - User-owned tables (if accessed during workflow): create a user-scoped client via `get_user_supabase_client(<user_jwt>)` to honor RLS, or write via controlled service-role APIs with explicit policies.
  - Provider Calls: Exa via `EXA_API_KEY`; LLM via Azure/OpenAI keys. User JWTs are not needed for provider calls unless you design per-user provider credentials later.

Why `DEV_TEST_USER_TOKEN`?
- Your HTTP routes (e.g., `/exa/*`) enforce `Authorization: Bearer <supabase_access_token>` with audience checks. The dev worker does not call these HTTP routes; it calls Exa SDK directly. Therefore, a user token is not needed for Exa.
- If/when the workflow needs to read/write user‑scoped data under RLS (e.g., user memory, saved items), we’ll use `get_user_supabase_client(<token>)`. The token in env lets the dev worker simulate that context without the front‑end.
- You can mint this via your `backend/supa_mind_test_token.sh` script. Profile creation is optional; an Auth user exists independently of `profiles`. If needed, create a `profiles` row via the Profiles API or migration snippet.

Lifecycle Summary
- Enqueue: ticker selects due schedules and enqueues jobs with an idempotency key (minute bucket) to avoid duplicates.
- Execute: worker claims the oldest queued job, starts a run, executes the deterministic workflow, finishes the run with metrics, and marks the job as succeeded/failed.
- Advance: ticker advances `next_run_at` per cadence. We start with PT-style intervals (PT30M/PT1H); cron support can be added later without changing public interfaces.

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

## Demo Note

The previous E2E demo script that created a schedule named `e2e-scheduler-demo` has been removed. The ticker proactively disables any schedule with that exact name if found. Use real user Streams and their schedules for testing. For ad‑hoc tests, enqueue jobs directly via the API or by inserting into `jobs` with clear metadata.
