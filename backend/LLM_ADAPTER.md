# LLM Adapter Specification (Azure OpenAI + OpenAI)

Goal
- Provide a stable, provider-agnostic interface for chat/completions.
- Normalize errors and usage metrics; enable retries and rate limiting.

Non-Goals (for now)
- Function/tool calling orchestration beyond simple pass-through.
- Prompt safety scanning (placeholder hooks only).

Core Interface (conceptual, not code)
- create_client(provider_config): returns a client bound to a provider.
  - provider_config (union):
    - AzureOpenAI: { endpoint, api_version, api_key, default_deployment }
    - OpenAI: { api_key, base_url?, organization? }
- chat(request): returns { id, model, created, usage, choices[], provider_meta }
  - request: {
    - model: string (or deployment for Azure)
    - messages: [{ role: system|user|assistant|tool, content: string | parts }]
    - temperature?: number, top_p?: number, max_tokens?: number, stop?: string[]
    - user?: string, metadata?: object, stream?: boolean
  }
- map_errors(provider_error): normalized { code, message, retry_after?, provider_code, status }
- compute_cost(usage, model): optional; estimate based on model pricing table (configurable, not hard-coded)

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
- Global defaults from environment (see `backend/ENVIRONMENT.md`).
- Per-request overrides allowed (model, temperature, etc.).
- Allow mapping canonical model aliases to provider-specific deployments (e.g., `gpt-4o` → Azure deployment).

Testing Strategy
- Contract tests with mocked HTTP to validate request shapes and error mapping.
- Golden tests for usage normalization and streaming assembly (once added).
- Simulate rate limits and ensure backoff behavior.

Change Log
- 2025-08-26 — Initial adapter interface and policies.
