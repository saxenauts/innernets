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
- [ ] Normalize errors and usage metrics
  - Notes: provider HTTP errors mapped to `ProviderError` JSON in exception; usage parsed from provider payload.
- [ ] Add retry/backoff and rate-limit handling
  - Notes: implement exponential backoff with jitter on 429/5xx and honor `Retry-After`.
- [x] Tests: contract/error (usage parsed)
- [x] Live tests: structured outputs across 4 functions (Azure)
- [ ] Optional: streaming support

Phase 4 — Scheduler & Jobs
- [x] Create migrations for schedules/jobs/runs tables
- [ ] Implement ticker (poller) and job enqueuer
- [ ] Implement executor (idempotent run wrapper)
- [ ] Observability: metrics + logs + run audit trail
- [ ] Tests: idempotency, retry, cron/interval calculations

Phase 5 — Search Agent (Exa-first, SDK contract)
- [ ] Define internal contracts for the two-step loop (inputs/outputs)
- [ ] Implement Step A/B orchestration (no UI yet)
- [ ] Persist queries/results and per-run metrics
- [x] Backend Exa endpoints (search + contents), caps + cost metering
- [ ] Guardrails: caps on queries/reads, novelty share
- [ ] Tests: cost caps, latency budget, correctness invariants

New — Job System Bring-up (dev)
- [ ] Add scheduler usage docs with env (DEV_TEST_USER_TOKEN) and dev run instructions
- [ ] Add `scheduler.jobs` helpers and `scheduler.worker` dev loop
- [x] Add `agents.search_workflow` orchestration with metrics
- [ ] Add tests: enqueue/claim/execute finishes a run and marks job done
- [ ] Add script/entry to run a one-shot job for a test user

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
- [ ] Centralize prompts with JSON Schema guidance for all functions
- [ ] Use consistent, minimal system prompts and parameterized user prompts
- [ ] Validate and self-correct patterns standardized across providers

Status Summary
- Done so far: backend DB scaffold, Supabase auth (profiles API), and LLM adapter with prompts for 4 functions.
