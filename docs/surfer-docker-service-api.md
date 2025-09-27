---
title: Service API
description: "HTTP endpoints exposed by the dev server (used as the service API)"
---

# Service API

Base URL
- Default: `http://127.0.0.1:8001`

Note: For a high-level overview of the Surfer and search-only loops that consume these endpoints, see `docs/search-loop.md`.

Envelope
- Most JSON responses use `{ result, logs }` where `result` is the structured payload and `logs` contains captured stdout/stderr.
- Exception: `/api/read-markdown` returns a minimal object `{ content, references }` only.

Endpoints
- POST `/api/google-search`
  - Body: `{ query: string, cdp_url?: string, headless?: boolean }`
  - Returns: normalized SERP items `{ position, title, link, raw_link, host }[]` and logs.
- POST `/api/read-markdown`
  - Body: `{ url: string, cdp_url?: string, headless?: boolean, citations?: boolean, prune?: boolean }`
  - Returns: `{ content: string, references?: string }` (no logs).
- POST `/api/ui-agent`
  - Body: `{ provider: string, model?: string, url: string, task: string, cdp_url?: string, headless?: boolean, grounding?: string }`
  - Returns: summary (provider/model/url/task/headless/cdp_url) and logs.
- POST `/api/explorer`
  - Body: `{ instruction: string, cdp_url?: string, headless?: boolean, max_steps?: number, search_concurrency?: number, read_concurrency?: number, batch_size?: number, max_depth?: number, stream_context?: string }`
  - Default behavior: returns HTTP 202 with `{ job_id, status_url, logs_url, result_url }`. Append `?sync=true` to block until the job completes and receive curated results directly (dev only).
- POST `/api/explorer/mock` (dev)
  - Purpose: returns a fixed mock response after a short delay (default 20s) to enable quick integration testing.
  - Query: `delay_s` (optional, default `20.0`).
  - Body: accepts the same shape as `/api/explorer` but is ignored.
  - Returns: `ExplorerResponse` (curations list) shaped identically to real runs.
- POST `/api/explorer/jobs`
  - Same body as `/api/explorer`.
  - Returns HTTP 202 with `{ job_id, status_url, logs_url, result_url }`.
- GET `/api/jobs/{job_id}`
  - Returns job state `{ job_id, state, created_at, started_at?, updated_at?, finished_at?, progress, artifacts_dir?, error? }` (timestamps ISO-8601).
- GET `/api/jobs/{job_id}/logs`
  - Returns accumulated stdout/stderr as plain text (captured via a tee during the run).
- GET `/api/jobs/{job_id}/result`
  - Returns `ExplorerResponse` (curations list) when the job finishes successfully.
- POST `/api/jobs/{job_id}/cancel`
  - Sets the cancel flag and responds with `{ status: "accepted" }`.

Notes
- The web UI at `/` is a simple playground for these endpoints.
- Use a persistent browser profile (`.artifacts/pw-user`) via the browser service for fewer bot checks and stable identity.
- `/api/step-probe` and `/api/step-probe-suite` are diagnostic endpoints for the planner; they are optional.

Health and version
- GET `/healthz` → `{ status: "ok", cdp_url?: string | null, version: {...} }`
- GET `/version` → `{ package?: string, fastapi?: string, python: string }`

CORS
- Configure allowed origins via `SURFER_CORS_ORIGINS` (comma-separated) or `*` to allow all.

Examples (curl)
```bash
# Google search
curl -s http://127.0.0.1:8001/api/google-search \
  -H 'content-type: application/json' \
  -d '{"query":"agentic browsing","headless":true}' | jq .

# Read markdown (minimal response)
curl -s http://127.0.0.1:8001/api/read-markdown \
  -H 'content-type: application/json' \
  -d '{"url":"https://example.com","headless":true}' | jq .

# UI agent
curl -s http://127.0.0.1:8001/api/ui-agent \
  -H 'content-type: application/json' \
  -d '{"provider":"anthropic","model":"claude-sonnet-4-20250514","url":"https://example.com","task":"Open the homepage","headless":false}' | jq .

# Explorer (async job submit)
curl -s -X POST http://127.0.0.1:8001/api/explorer/jobs \
  -H 'content-type: application/json' \
  -d '{"instruction":"Research Crawl4AI best practices","headless":true,"max_steps":3,"stream_context":"This stream is about Crawl4AI usage; add novel findings only."}' | jq .

# Explorer (sync dev mode)
curl -s "http://127.0.0.1:8001/api/explorer?sync=true" \
  -H 'content-type: application/json' \
  -d '{"instruction":"Research Crawl4AI best practices","headless":true,"max_steps":3,"stream_context":"Stream context paragraph here"}' | jq .

# Dev mock (fast integration)
curl -s -X POST "http://127.0.0.1:8001/api/explorer/mock?delay_s=2" \
  -H 'content-type: application/json' \
  -d '{"instruction":"ignored","headless":true,"max_steps":1}' | jq .
```

## Where things get stored

- Logs are kept in memory per job and mirrored to the container console. `/logs` returns exactly what the run printed.
- Results come from the Explorer’s structured output (curations). `/result` returns an easy list of `{summary, links[]}` for downstream use.
- Artifacts (JSON, optional markdown) are written under `.artifacts/devserver/explorer-<timestamp>/` and the folder path appears in job status.
