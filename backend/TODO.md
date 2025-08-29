# Backend TODO (Milestones)

Phase 0 — Docs & Foundations
- [x] Create backend folder and AGENTS.md
- [x] Draft ENVIRONMENT.md with variables
- [x] Draft SCHEMA.md (non-SQL outline)
- [x] Draft LLM_ADAPTER.md (interface/spec)
- [x] Draft SCHEDULER.md (design)

Phase 1 — Scaffolding (no business logic yet)
- [x] Decide Python framework (FastAPI) — updated AGENTS
- [x] Create basic project structure (`backend/src`, `backend/tests`) with minimal app and health endpoint
- [x] Add top-level `.gitignore`, `.env.example`, `.env.dev`, `.env.prod`
- [x] Switch to Poetry packaging (`backend/pyproject.toml`)
- [ ] Choose logging libs and structure fields (trace_id, job_id, user_id)

Phase 2 — Environment & Clients
- [x] Implement minimal env loader (config module)
- [x] Add Supabase client factory (service role)
- [ ] Wire structured logging and request context helpers

Phase 3 — LLM Adapter (Azure/OpenAI)
- [x] Implement adapter baseline (function-first, non-stream)
- [x] Normalize errors and usage metrics
  - Notes: provider HTTP errors mapped to `ProviderError` JSON in exception; usage parsed from provider payload.
- [ ] Add retry/backoff and rate-limit handling
  - Notes: implement exponential backoff with jitter on 429/5xx and honor `Retry-After`.
- [x] Tests: contract/error (usage parsed)
- [x] Live tests: structured outputs across 4 functions (Azure)

Phase 4 — Scheduler & Jobs
- [x] Create migrations for schedules/jobs/runs tables
- [x] Implement ticker (poller) and job enqueuer (includes schedule meta payload hydration, due-filter hardening)
- [x] Implement executor (idempotent run wrapper) — `worker.run_once` and in-app runner thread
- [ ] Observability: metrics + logs + run audit trail (basic logs done; expand structured fields later)
- [x] Tests: enqueue/claim/execute, ticker cadence advance

Phase 5 — Search Agent (Exa-first, SDK contract)
- [x] Define internal contracts and implement orchestration in `agents.search_workflow`
- [x] Persist curations per run (clusters+links) and mark finished_at on completion
- [x] Exa client wrapper + caps + cost accounting in workers (no public endpoints)
- [ ] Guardrails: caps on queries/reads, novelty share
- [ ] Tests: cost caps, latency budget, correctness invariants
- [ ] Improve cost accounting granularity across steps (search vs contents per round), and include token costs (prompt/completion, per step)

New — Job System Bring-up (dev)
- [x] Add scheduler usage docs and demo; in-app runner and Procfile added
- [x] Add `scheduler.jobs` helpers and `scheduler.worker` loop
- [x] Add `agents.search_workflow` orchestration with metrics
- [x] Add tests: enqueue/claim/execute and ticker
- [x] Add script/entry to run worker and demo

Phase X — Operations
- [ ] Add simple CI (lint, type check, docs check)
- [ ] Add error reporting (Sentry) and telemetry (OTel) hooks
- [ ] Document runbooks and on-call basics

Notes
- Keep `docs/updates.md` in sync when tasks move between phases.
- Keep `backend/SCHEMA.md` and `backend/AGENTS.md` updated with decisions.

 Profiles Milestone (minimal)
- [x] Add minimal `profiles` schema + RLS (migration 0001)
- [x] Add Supabase runbook (link, apply, verify)
 - [x] API: add GET/PUT `/me/profile` (FastAPI)
 - [x] Auth: replace dev header with Supabase JWT verification
 - [ ] Frontend: wire profile view/edit — TODO
- Prompt Refactor (new)
- [x] Centralize prompts with JSON Schema guidance for all functions
- [x] Use consistent, minimal system prompts and parameterized user prompts
- [x] Validate and self-correct patterns standardized across providers

Status Summary
- Done so far: backend DB scaffold, Supabase auth (profiles API), LLM adapter with structured outputs, scheduler ticker/worker with demo and in-app runtime.
- Done so far: search step functions with prompts


Streams & Frontend Integration (new)
- [x] Add SQL: `streams`, `urls`, `curation_runs`, `curation_clusters`, `curation_cluster_links` (RLS)
- [x] Streams API: POST/GET/PUT `/streams`, POST `/streams/:id/run`, GET `/streams/:id/latest`
- [x] Orchestrator: persist curations; derive `stream_id` from schedule meta for scheduled runs
- [x] Frontend login via Supabase password grant (anon key + project URL)
- [x] Frontend pages call Streams API (create/list/get/latest, Run Now)
- [ ] Add GET `/streams/:id/runs` (history) and optional aggregate endpoint
- [ ] Frontend: add past runs view + auto-poll after Run Now
- [ ] Token refresh (supabase-js) instead of raw fetch grant; handle expiry gracefully
- [ ] Improve CORS configuration for different environments
