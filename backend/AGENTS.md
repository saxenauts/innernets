# Backend Agents Guide

Scope: Python backend for InnerNets. Starts with a search-based service driven by a user-defined schedule. This doc captures principles, architecture, conventions, and pointers to evolving specs.

## Principles
- Clear contracts: typed domains, explicit request/response shapes in docs before code.
- Evolutionary design: small, testable increments; schema and docs evolve in lockstep.
- Operational clarity: structured logs, trace IDs, predictable errors, and idempotency for jobs.
- Security-first: least-privilege DB access, no secrets in repo, input validation, OWASP basics.
- Portability: provider-agnostic LLM adapter; scheduler that can scale or be swapped later.

## Initial Architecture (FastAPI chosen)
- API layer: FastAPI app (`backend/src/app/main.py`) with a minimal health endpoint.
- Search Agent service: consumes schedules, runs the Exa-first plan in `docs/search-only-plan.md` (coming next).
- Job Scheduler/Worker: polls due schedules and executes jobs; ensures idempotency and safe retries.
- LLM Adapter: unifies Azure OpenAI and OpenAI native under one interface.
- Data: Supabase (Postgres). Use service-role key server-side; never commit keys.

## Directories
- `backend/src/` — application code (FastAPI app + clients)
- `backend/tests/` — unit/integration tests (pytest)
- `backend/` docs — this folder (specs, schema, environment, TODO)

## Tooling
- Package manager: Poetry (per-service). See `backend/pyproject.toml`.
- Python: >= 3.11.
- Run: `cd backend && poetry install && poetry run uvicorn app.main:app --reload`.
- Env files: live in `backend/` (`.env.example`, `.env.dev`, `.env.prod`); create `backend/.env` for local runs.

## Specs & References
- Scheduler design: `backend/SCHEDULER.md`
- LLM Adapter spec: `backend/LLM_ADAPTER.md`
- Environment & config: `backend/ENVIRONMENT.md`
- Database schema (evolving): `backend/SCHEMA.md`
- Service plan: `docs/search-only-plan.md`

## Data Model (overview; see SCHEMA.md)
- Users: Supabase Auth users (canonical). Local `profiles` for app-specific fields.
- Schedules: user-defined cadence per Stream/mission; timezone-aware.
- Jobs & Runs: queued work and execution records with idempotency keys and metrics.
- Queries, Sources, Results: capture inputs and outcomes for auditability and learning.

## API & Contracts (early outline)
- Internal contracts first; public HTTP contracts later.
- Request/response examples to live in docs before endpoints exist.
- Stable error model (see “Error Model” below) across providers and services.

## Error Model (baseline)
- `BadRequest` (4xx): validation or contract mismatch.
- `Unauthorized`/`Forbidden`: authN/Z failures.
- `NotFound`: missing resources.
- `Conflict`: idempotency or version conflicts.
- `RateLimited`: backoff and retry hints included.
- `ProviderError`: normalized code/message; original provider code retained in metadata.
- `Internal`: unexpected; includes trace ID, no sensitive details.

## Scheduling Strategy (summary)
- Start with a DB-driven poller: a single worker periodically selects due schedules and enqueues jobs.
- Use DB row-level locking to prevent duplicate claims in multi-worker setups.
- Upgrade path: swap to a distributed queue (e.g., Celery/Redis) or managed scheduler; keep contracts stable.

## LLM Adapter Strategy (summary)
- Single interface for chat/completions with common params (`model`, `messages`, `temperature`, `top_p`, `max_tokens`, `stop`).
- Provider-specific config adapters: Azure (endpoint, api-version, deployment) and OpenAI native.
- Normalized usage metrics (prompt/completion tokens, cost estimation) and error taxonomy.
- Retries with jittered backoff on transient errors; transparent rate-limit handling.

## Observability
- Structured logs with contextual fields (user_id, schedule_id, job_id, run_id, provider, model, trace_id).
- Execution metrics per run: queries issued, pages read, token use, elapsed.
- Audit-friendly: store minimal necessary metadata; no raw secrets or full prompts where not needed.

## Security & Compliance
- Secrets only via environment or secret manager; never commit real keys.
- Principle of least privilege for DB role used by backend.
- Input validation and output encoding at boundaries.
- PII minimization: store only what’s necessary.

## Open Questions (to be resolved as we build)
- Queue/scheduler backing (simple poller vs. Celery/Redis vs. managed).
- Per-user provider keys support and storage (encryption, KMS, or delegated access).

## Supabase Client vs. Pydantic Models
- Use the official `supabase` Python client for DB access (server-side, with service role) for speed and to leverage PostgREST/Row Level Security semantics.
- Use Pydantic models for domain validation and API contracts. These complement the client; they are not alternatives.

## TDD Approach
- Write tests under `backend/tests/` before or alongside implementation.
- Keep tests fast and deterministic (mock external clients like Supabase and LLMs).

## Profiles API
- Endpoints: `GET /me/profile`, `PUT /me/profile` (see `src/app/routes/profile.py`).
- Auth: Supabase JWT via `Authorization: Bearer <access_token>`; verified with `SUPABASE_JWT_SECRET`.
  - Audience: tokens are issued with `aud = authenticated`; backend checks this via `SUPABASE_JWT_AUD` (default `authenticated`).
  - Startup: env is loaded from `.env` in the current dir; launch from `backend/` or set `DOTENV_PATH=backend/.env`.
- Data access: repository in `src/app/repositories/profile_repo.py` using the service-role client.
- Note: We will later wire full auth middleware and scopes as needed.

## How to Contribute (docs-first)
- Update the relevant spec in `backend/*` and the index in `AGENTS.md`.
- Update `backend/SCHEMA.md` when data shapes change.
- Log changes and move tasks in `docs/updates.md`.
