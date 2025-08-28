# Backend Environment & Configuration

This backend uses environment variables for all secrets and configuration. Do not commit real values. Use a local `.env` (gitignored) for development.

Core
- APP_ENV: `local` | `dev` | `staging` | `prod`
- LOG_LEVEL: `debug` | `info` | `warn` | `error`
- TZ: IANA timezone (e.g., `UTC`)

Database / Supabase
- SUPABASE_URL: Base URL of Supabase project
- SUPABASE_SERVICE_ROLE_KEY: Service role key (server-only). Treat with care.
- POSTGRES_CONNECTION_STRING: Optional direct Postgres URI if bypassing PostgREST
- SUPABASE_JWT_SECRET: JWT secret used to verify Supabase access tokens (Auth → Settings → API)
- SUPABASE_JWT_AUD: Expected JWT audience; defaults to `authenticated`.
- SUPABASE_ANON_KEY: Public anon key used to build user-scoped clients that enforce RLS.

Notes
- The backend loads env from `.env` via `load_dotenv(os.getenv("DOTENV_PATH", ".env"))`.
  - Start from `backend/` so `.env` is found, or set `DOTENV_PATH=backend/.env` when starting from repo root.

LLM Providers (Adapter)
- PROVIDER: `azure_openai` | `openai` (default can be overridden per request)
- OPENAI_API_KEY: Key for OpenAI native
- OPENAI_ORG: Optional org id
- OPENAI_BASE_URL: Optional base URL override
- AZURE_OPENAI_ENDPOINT: e.g., `https://<name>.openai.azure.com`
- AZURE_OPENAI_API_VERSION: e.g., `2024-02-15-preview`
- AZURE_OPENAI_API_KEY: Azure key
- AZURE_OPENAI_DEPLOYMENT_NAME: Azure deployment name (e.g., `gpt-4o-mini`). Only this variable is used.
  - Azure specifics: Some deployments (e.g., `gpt-5`) require `temperature=1.0` and do not accept `max_tokens` in Chat Completions. The adapter accounts for this automatically.

Exa (Search + Contents)
- EXA_API_KEY: Exa API key from https://dashboard.exa.ai (required for workers)
- EXA_BASE_URL: Optional override; defaults to `https://api.exa.ai`
 - DEV_TEST_USER_TOKEN: Optional Supabase JWT for a test user to run the agent loop locally without frontend. Do not commit real tokens.

Notes
- For neural/auto searches, we enforce `numResults ≤ 25` to stay within the low-cost tier.
- Our API responses include `provider_cost` mirroring Exa's `costDollars` breakdown.

LLM Adapter Options (per request)
- tool_choice: `auto` | `required` | `none` | `function` (we default to function-first; force a specific tool when deterministic)
- strict: enable schema-conformant arguments (recommended true)
- max_tokens, temperature, top_p: standard knobs

Scheduling
- SCHEDULE_POLL_INTERVAL_MS: Default poll interval for DB-driven scheduler (e.g., `30000`)
- SCHEDULE_MAX_JOBS_PER_TICK: Backpressure control (e.g., `25`)
- SCHEDULER_IN_APP: `1` to run background scheduler thread inside FastAPI (used by `app.run_backend`)

Demo (optional)
- DEMO_LAG_AFTER_TICK, DEMO_LAG_BEFORE_THIRD, DEMO_LAG_BETWEEN_RUNS, DEMO_SECOND_TICK_DELAY_SEC: small timing lags to observe queue and processing in demo script

Telemetry (Optional)
- SENTRY_DSN: error reporting
- OTEL_EXPORTER_OTLP_ENDPOINT: OpenTelemetry collector endpoint

Local Setup (docs-first)
- Use backend env files: `backend/.env.example` (template), `backend/.env.dev`, `backend/.env.prod` (placeholders only). Do not store real secrets in git.
- Create a real `backend/.env` locally by copying from `backend/.env.dev` and filling values: `cd backend && cp .env.dev .env`.
- For shared dev, use a secure secret sharing method (1Password/Bitwarden).

Supabase Setup (quick start)
- Create a project at https://supabase.com/ (free tier is fine to start).
- In your project, go to Settings → API:
  - Copy the Project URL into `SUPABASE_URL`.
  - Copy the Service Role Key into `SUPABASE_SERVICE_ROLE_KEY` (server-side only).
- Optional: Database → Connection Strings → Postgres. Copy the URI into `POSTGRES_CONNECTION_STRING` if you prefer direct DB access.
- Keep Row Level Security on (default). We will define policies with migrations later.

Dev Test Token Generation
cd backend & bash ./supa_mint_test_token.sh free@meme.com hehemama

Change Log
- 2025-08-26 — Initial environment matrix for DB, providers, scheduling, telemetry.
