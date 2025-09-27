---
title: Docker Service Integration Guide
description: One-stop guide to run and integrate the AI Surfer Docker service from another repo
---

# AI Surfer Docker Service — Integration Guide

This document is the single reference you need to run the AI Surfer Docker service and integrate it from another product. It covers what the service does, how to run it, the API contract (request/response shapes), and which artifacts you should persist and commit for a smooth setup.

Note: For a high-level view of the exploration loops used by the product, see `docs/search-loop.md`.

## What the Service Does

- Launches a real Chromium browser (Patchright/Playwright) in the container and exposes a simple HTTP API.
- Runs long, multi‑step “Explorer” jobs that search, read pages, and return curated results.
- Handles concurrency via one browser with per‑job isolated contexts/tabs.
- Streams logs and persists results + metadata to disk so you can retrieve them later (even after restarts).

## TL;DR — Run It

Prereqs: Docker installed. From the repo root:

```bash
docker compose up --build
```

What this does:
- Starts an internal browser on `9222` and the API on `8000`.
- Binds your repo `./.artifacts` to `/app/surfer-agent/.artifacts` inside the container to persist logs/results/configs.

Health check:
```bash
curl -s http://127.0.0.1:8001/healthz | jq .
```

## Environment & Artifacts

The service uses `ARTIFACTS_DIR` (default `/app/surfer-agent/.artifacts`) to persist:
- Browser user profile: `.artifacts/pw-user/` (baseline Chromium profile; helps warmups and logins).
- Warmup cookies: `.artifacts/google_cookies.json` (optional, if you preload cookies).
- Job metadata DB: `.artifacts/devserver/jobs.sqlite` (durable job index across restarts).
- Per‑job folders: `.artifacts/devserver/explorer-<timestamp>/` containing `result.json` and `run.log`.

Repo policy (already configured):
- Tracked (committed):
  - `.artifacts/devserver/jobs.sqlite`
  - `.artifacts/google_cookies.json`
  - `.artifacts/pw-user/` (baseline profile)
- Not tracked (ignored):
  - `.artifacts/devserver/explorer-*/` (run logs/results)
  - `.artifacts/devserver/jobs.sqlite-wal` and `jobs.sqlite-shm`
  - `.artifacts/tmp/`, `.artifacts/ws.json`, `.artifacts/xdg-*`

Tip: For production images, set `UVICORN_RELOAD=false` to disable dev hot‑reload.

## Core Endpoints

Base URL: `http://127.0.0.1:8001`

1) Submit Explorer Job (async)
- POST `/api/explorer`
- Body:
```json
{
  "instruction": "Research agentic browsing",
  "headless": true,
  "max_steps": 2,
  "stream_context": "Optional: a paragraph of the current stream context to bias LLM calls"
}
```
- Response (202 Accepted):
```json
{
  "job_id": "job_2d5e9f838ec6",
  "status_url": "http://127.0.0.1:8001/api/jobs/job_2d5e9f838ec6",
  "logs_url": "http://127.0.0.1:8001/api/jobs/job_2d5e9f838ec6/logs",
  "result_url": "http://127.0.0.1:8001/api/jobs/job_2d5e9f838ec6/result"
}
```

2) Check Job Status
- GET `/api/jobs/{job_id}`
- Response:
```json
{
  "job_id": "job_2d5e9f838ec6",
  "state": "queued | running | completed | failed | canceled",
  "created_at": "2025-09-24T20:25:20+00:00",
  "started_at": "2025-09-24T20:25:21+00:00",
  "updated_at": "2025-09-24T20:26:59+00:00",
  "finished_at": "2025-09-24T20:26:59+00:00",
  "progress": {"stage": "running|completed"},
  "artifacts_dir": "/app/surfer-agent/.artifacts/devserver/explorer-20250924-202520",
  "error": null
}
```

3) Fetch Logs
- GET `/api/jobs/{job_id}/logs`
- Response: `text/plain` (tee’d stdout/stderr of the run). Use for streaming or post‑mortem.

4) Fetch Results (curations)
- GET `/api/jobs/{job_id}/result`
- Response shape:
```json
{
  "curations": [
    {
      "id": 1,
      "summary": "Short human‑readable synthesis of the finding",
      "links": [
        {"id": 1, "title": "Page title", "url": "https://example.com/page"}
      ]
    }
  ]
}
```

Notes
- The service returns 409 on `/result` if the job hasn’t finished.
- After restart, the service resolves job status/results from SQLite + files under `.artifacts/devserver/`.

## Recommended Client Flow (Other Product)

Minimal, robust pattern:
1. Submit a job. Store the `job_id`.
2. Poll `status_url` every 2–5 seconds until `state` is final.
3. Fetch `logs_url` for debugging; fetch `result_url` for the curations payload.
4. Handle 409 on `/result` by retrying later; handle 404 as “unknown job id”.

Example (curl):
```bash
JOB=$(curl -s http://127.0.0.1:8001/api/explorer \
  -H 'content-type: application/json' \
  -d '{"instruction":"Research agentic browsing","headless":true,"max_steps":2,"stream_context":"This stream is about agentic browsing stacks; focus on new, high-signal findings that add to this."}')
JOB_ID=$(echo "$JOB" | jq -r .job_id)

# Poll
while true; do
  STATE=$(curl -s http://127.0.0.1:8001/api/jobs/$JOB_ID | jq -r .state)
  echo state=$STATE
  if [ "$STATE" = "completed" ] || [ "$STATE" = "failed" ] || [ "$STATE" = "canceled" ]; then
    break
  fi
  sleep 2
done

# Results
curl -s http://127.0.0.1:8001/api/jobs/$JOB_ID/result | jq .
```

## Configuration Cheatsheet

Environment variables (see `docker-compose.yml`):
- `PORT` (default `8001`) — API port.
- `BROWSER_PORT` (default `9222`) — internal CDP.
- `ARTIFACTS_DIR` (default `/app/surfer-agent/.artifacts`) — persisted volume.
- `BROWSER_ENABLED` (default `true`) — launch internal browser.
- `HEADFUL` (default `true` in compose) — headful desktop (VNC/noVNC) or headless.
- `UVICORN_RELOAD` (default `true` in compose) — enable dev reload; set to `false` for production.
- Concurrency/backpressure (optional):
  - `CTX_POOL_MAX` (default 3)
  - `JOBS_MAX_CONCURRENT` (default 2)
  - `JOBS_QUEUE_MAX` (default 16)
  - `JOBS_RESULT_TTL_SEC` (default 900)

Provider API keys (set via `.env` mounted by compose):
- Anthropic: `ANTHROPIC_API_KEY`
- OpenAI: `OPENAI_API_KEY`
- Azure OpenAI: `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT_NAME`
- OpenRouter: `OPENROUTER_API_KEY`
- Grounding (optional): `MOONDREAM_API_KEY`

## Persistence Gotchas (Read This)

- Always run `docker compose up` from the repo root so `./.artifacts` bind‑mounts correctly.
- Do not delete or rename `./.artifacts` between runs if you want job history to survive.
- `jobs.sqlite` is committed by policy; `jobs.sqlite-wal` and `jobs.sqlite-shm` are ephemeral and ignored.
- For consistent behavior in production, set `UVICORN_RELOAD=false`.

## Support Notes

- The service persists job metadata (job id, state, artifact paths) in SQLite and writes results/logs to files. After restart, you can still query status/results.
- Each job runs in an isolated browser context; tabs are scoped to the job and cleaned up on completion.

If anything is unclear for your integration team, point them to this doc first—no need to dive into internal modules.
- Dev Mock Endpoint (for fast integration)
  - POST `/api/explorer/mock?delay_s=2`
  - Returns a fixed curated response after the given delay (seconds). The request body is accepted for shape compatibility but ignored.
  - Use this to wire up your client without waiting for real exploration to finish; then switch to `/api/explorer` when ready.
