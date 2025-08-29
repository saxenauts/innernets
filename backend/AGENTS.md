# Backend Agents Guide

Scope: Python backend for InnerNets. Starts with a search-based service driven by a user-defined schedule. This doc captures principles, architecture, conventions, and pointers to evolving specs.

## Principles
- Clear contracts: typed domains, explicit request/response shapes in docs before code.
- Evolutionary design: small, testable increments; schema and docs evolve in lockstep.
- Operational clarity: structured logs, trace IDs, predictable errors, and idempotency for jobs.
- Security-first: least-privilege DB access, no secrets in repo, input validation, OWASP basics.
- Portability: provider-agnostic, function-first LLM adapter; scheduler that can scale or be swapped later.

## Architecture (FastAPI + Scheduler + Streams)
- API layer: FastAPI app (`backend/src/app/main.py`) with a minimal health endpoint.
- Streams API: user-created Streams (`mission`, `sources` → stored as `sources_hints`, `cadence`) with CRUD (POST/GET/PUT/DELETE) and Run Now; latest curations and paginated runs endpoints.
- Search Agent service: consumes streams and schedules, runs the Exa-first plan (LLM steps centralized in `llm/search_steps.py`).
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
- Streams: user-defined mission + cadence (+ optional sources_hints) with RLS.
- URL registry: global table of URLs with optional title/description; updated opportunistically.
- Curations: per-run clusters with linked URL IDs; owned via stream → run.
- Schedules: user-owned cadence rows; created when a stream is created; `meta.stream_id` ties schedule to stream.
- Jobs & Runs: queued work and execution records with idempotency; ticker enqueues, worker claims and executes.

## API & Contracts (typed via Pydantic)
- Rule: service boundaries return and accept Pydantic models — no plain dicts.
- Internal contracts first; public HTTP contracts later if needed.
- Request/response examples belong in docs and Pydantic classes in code.
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

## Scheduler Runtime Modes
- In-App (default for `app.run_backend`): a background thread runs the ticker and worker loop inside FastAPI. Toggle with `SCHEDULER_IN_APP=1`.
- Split Processes: run API and worker separately (see `app.scheduler.worker_main`). Keep exactly one ticker process to avoid redundant enqueues.
- Demo note: The old `app.scheduler.demo` has been removed to avoid accidental demo schedules. Use real Streams and schedules for testing.

## LLM Adapter Strategy (summary)
- Structured JSON first: single-entrypoint `structured(instruction, context, schema)` returning Pydantic-validated outputs.
- Provider adapters: Azure OpenAI (Chat Completions + `response_format=json_object`) and OpenAI native (TBD).
- Normalized usage metrics and error taxonomy; raise `ProviderError` on failures.
- Determinism controls: schema guidance and temperature; minimal retries with a one-shot self-correction on validation errors.

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
- Data access: user-scoped Supabase client (RLS enforced). We build a per-request client with `SUPABASE_ANON_KEY` and set the user's token on PostgREST.
- Service-role usage: reserved for internal jobs and migrations; not used in user endpoints.

## Exa Search (SDK-first, no public routes)
- Workers call a thin service wrapper over `exa-py` (`app/clients/exa_client.py`).
- Contract: Python SDK signature (snake_case, top-level `text/highlights/summary`).
- Models: Pydantic response types in `app/clients/exa_schemas.py` (`SearchResponse`, `ContentsResponse`, etc.).
- Caps: enforce `num_results ≤ 25` for `neural/auto`, `≤ 100` for `keyword` per plan.
- Attribution: attribute costs to `jobs.user_id` via run metrics; no user JWT required for provider calls.

## How to Contribute (docs-first)
- Update the relevant spec in `backend/*` and the index in `AGENTS.md`.
- Update `backend/SCHEMA.md` when data shapes change.
- Log changes and move tasks in `docs/updates.md`.
- Prompt architecture: adopt JSON Schema-guided prompts for all functions; centralize and refactor prompt templates after functions are stable.
- Agents rule: return Pydantic models at boundaries (no plain dicts); define schemas alongside agents.

## Search Workflow (LLM steps, ID-first)
- Location: `backend/src/app/llm/search_steps.py`
- Steps:
  - Generate 5 queries with routing (`query_type: keyword|neural`).
  - Filter candidates (LLM) from the full deduped set (no cap) → return 2–3 `selected_ids` (IDs only).
  - Propose 3–6 follow-up queries (diversity and adjacency).
  - Consolidate curations → 2–6 clusters with `title`, `hook`, and 3–4 `link_ids`.
- Orchestrator: `backend/src/app/agents/search_workflow.py` assigns IDs ("01", "02", …), maps IDs ↔ URLs, reads contents for selected IDs, runs follow-up search, and consolidates.
- Token discipline: pass compact context (title, domain, short snippets/summaries). LLMs never see raw URLs. Temperature is fixed at 1.0 across steps.
- Context wiring: at t=0 `additional_context_json = {}`; at t>0 pass compact summary of the latest run (`curations_repo.get_previous_context`).
- Exa routing: 25 results per query; `keyword` vs `neural` per item.

## LLM Structured Outputs Notes
- Integer fields: prompts and provider system message emphasize whole numbers for integer-typed fields.
- Repair attempt: on validation failure, the adapter performs one repair call with the validation error details to elicit corrected JSON.


### Streams endpoints
- POST `/streams` — body: `{ mission: string, sources?: string, cadence: 'daily'|'3xweek'|'weekly'|'discovery', time_zone?: string }`
- GET `/streams` — lists active streams for the user.
- GET `/streams/:id` — stream details.
- PUT `/streams/:id` — body: `{ mission?, sources?, cadence?, time_zone? }` (sources maps to `sources_hints`).
- DELETE `/streams/:id` — soft-delete (sets `active=false` and disables schedule).
- POST `/streams/:id/run` — enqueue ad-hoc run.
- GET `/streams/:id/latest` — latest run summary (includes `clusters[].links` joined via `curation_cluster_links.url_id → urls.id`).
- GET `/streams/:id/runs?limit=10&before=iso` — reverse-chronological paginated runs. Each run contains `clusters[]` with `links` joined via the same FK.

### Output shape for frontend
- Curations (final): `{ title, hook, links: [{ url, title?, domain, position }], position }`.
- `links` are resolved database joins (no metrics fallback): `curation_cluster_links.url_id` → `urls(id)`.
- New runs normalize LLM `link_ids` to zero‑padded IDs when persisting, ensuring consistent URL mapping.

### Frontend integration checklist
- Auth: use Supabase access token in `Authorization: Bearer <token>` for all user‑scoped endpoints.
- Streams: implemented (`POST/GET/PUT /streams`, `POST /streams/:id/run`).
- Results: implemented (`GET /streams/:id/latest`) with resolved links.
- UI: render curations (title + hook + links); "Run Now" triggers a job; scheduled runs will append curations per cadence.
