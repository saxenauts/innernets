# LLM Adapter Specification (Azure OpenAI + OpenAI)

Goal
- Provide a stable, provider-agnostic, function-first interface for workflows.
- Normalize errors and usage metrics; enable retries and rate limiting.

Non-Goals (for now)
- General chat UX or message assembly; focus is tool invocation.
- Prompt safety scanning (placeholder hooks only).

- Core entrypoints
  - structured({ instruction, context, schema{name, schema} }, options) -> output (validated JSON per schema)
- map_errors(provider_error): normalized { code, message, retry_after?, provider_code, status }
- compute_cost(usage, model): optional; configurable pricing table (not hard-coded)

Streaming (later)
- Support streaming via callback or async iterator interface.
- Merge partial deltas into final message for non-stream consumers.

Retries & Rate Limiting
- Exponential backoff with jitter on 429/5xx and transient network failures.
- Respect `retry_after` if provided by provider.
- Surface a clear `RateLimited` error when exhausted.

Telemetry
- Log: provider, model, latency_ms, status, token_usage, request_size, response_size, trace_id.
- Include minimal request metadata (no secrets, no full prompts unless explicitly enabled for debugging).

Configuration
- Global defaults from environment (see `docs/backend-environment.md`).
- Per-request overrides allowed (model, temperature, etc.).
- Allow mapping canonical model aliases to provider-specific deployments (e.g., `gpt-4o` → Azure deployment).

Testing Strategy
- Contract tests with mocked HTTP to validate request shapes and error mapping.
- Golden tests for usage normalization and streaming assembly (once added).
- Simulate rate limits and ensure backoff behavior.

Azure Notes
- Uses Chat Completions exclusively for structured JSON, with `response_format=json_object` and client-side Pydantic validation.
- Enforces `temperature=1.0` for consistent structured outputs.
- Adds schema-aware steering (top-level keys and array item keys) and a single self-correction pass if validation fails.

Change Log
- 2025-08-26 — Initial adapter interface and policies.
- 2025-08-27 — Implemented function-first adapter with Azure provider and tool registry scaffolding.
- 2025-08-27 — Added structured-output entrypoint to avoid chat/tool selection; aligns with workflow steps.
- 2025-08-27 — Simplified Azure provider: try Responses API; on any failure, fall back to Chat Completions with json_object and client-side schema validation. Handles gpt-5 Azure specifics (temperature=1.0, no max_tokens parameter).


Search Steps (where schemas live)
- `backend/src/app/llm/search_steps.py` defines Pydantic models + wrappers for:
  - GenerateQueriesOut (5 queries; each has `query`, `query_type`)
  - FilterCandidatesOut (`selected_ids: List[str]`)
  - ProposeFollowupsOut (3–6 follow-up queries)
  - ConsolidateOut (`curations` with `title`, `hook`, `link_ids`)
- Prompts in `backend/src/app/llm/prompts.py` use double‑braced variables and are substituted programmatically.

