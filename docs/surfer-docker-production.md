---
title: Production Readiness (Headful) & Sizing
description: "Headful-by-default deployment: hardware sizing, Docker flags, warmup debugging, and hardening"
---

# Production Readiness & Sizing

This guide consolidates everything needed to run the Surfer Agent service in production with a headful browser (Xvfb + VNC/noVNC inside the container): VM sizing, container resource flags, environment configuration, warmup/runbook steps, and hardening. It assumes you deploy the service in a Docker container on a fresh VM (e.g., Azure) and that your “real product” will also run inside the same container.

## What Runs (At a Glance)
- One long‑lived Chromium (Patchright/Playwright) with CDP on port `9222` and a persistent profile under `.artifacts/pw-user`.
- FastAPI service (Explorer, UI agent, Google adapter, Markdown readers) on `8001`.
- Headful desktop (Xvfb + fluxbox + VNC + noVNC) is the default. The viewer lets you see and interact with the exact Chromium instance used by the service.

Key files:
- Browser service (Chromium + CDP): `surfer-agent/src/browser_service/service.py`
- Browser harness/manager (single CDP attach, fairness): `surfer-agent/src/browser_service/harness.py`, `surfer-agent/src/browser_service/manager.py`
- Dev/Service API: `surfer-agent/devserver/app.py`, `surfer-agent/devserver/services.py`
- Docker entrypoint (orchestrates browser → warmup → API): `docker/entrypoint.sh`
- Dockerfile (Playwright base + venv + patchright): `Dockerfile`

## Concurrency Model
- One browser process per container (CDP).
- Per‑job isolation via Playwright `BrowserContext`s (pooled). Default envs:
  - `CTX_POOL_MAX` (default 3) — max concurrent contexts.
  - `JOBS_MAX_CONCURRENT` (default 2) — concurrent jobs.
- All Playwright operations are serialized fairly across jobs by a central scheduler, ensuring deterministic actions on a single CDP.

## Resource Sizing

RAM (rule‑of‑thumb):
- Baseline (Chromium + API): 0.8–1.2 GB
- Per concurrent job (context + tabs + Crawl4AI/markdown work): +0.5–1.0 GB
- Headful desktop stack (Xvfb+VNC+noVNC): +0.1–0.2 GB

CPU:
- Allocate 1–2 vCPUs per concurrent job for comfortable page rendering and image/markdown processing. LLM calls are remote and do not tax local CPU significantly.

Disk:
- Artifacts/profile volume `.artifacts`: 5–10 GB comfortable (profile can grow to ~0.5–2 GB; job artifacts accumulate, but retention prunes old runs).
- Consider a dedicated data disk for `.artifacts` if you want consistent IOPS and durability across container recreations.

Network:
- Outbound to provider APIs (Anthropic/OpenAI/Azure/OpenRouter) and optional Moondream grounding.
- Optional proxy for Google region/egress control (`PROXY_SERVER`).

### Azure Networking & Access
- Inbound ports:
  - `8001/tcp` — API (restrict to your product networks or VPN).
  - `6080/tcp` — noVNC web viewer (optional; restrict to admins only).
  - `5900/tcp` — VNC (optional; restrict to admins only).
- Outbound: allow HTTPS to LLM providers and Moondream; allow general web for crawling.
- NSG rules: explicitly allow only the ports above; deny all else from public internet.

## Azure VM Tiers (Headful, No GPU)

Pick based on expected concurrent jobs; headful is the default:
- Dev/PoC (headful, 1 job): 2 vCPU / 8 GB / 30–50 GB SSD — e.g., D2as v5
- Small prod (headful, up to 2 concurrent jobs): 4 vCPU / 16 GB / 64+ GB — e.g., D4as v5
- Medium prod (headful, 2–3 jobs + headroom): 8 vCPU / 32 GB / 128+ GB — e.g., D8as v5

Notes:
- Headful includes an X server and VNC/noVNC; budget ~0.1–0.2 GB RAM for it.
- Avoid B‑series (burstable) for steady workloads; D‑series is more predictable.
- If you later self‑host a vision model, a GPU VM may be required; not needed today because grounding is cloud by default.
- Chromium runs with `--disable-gpu`; no GPU is required on the VM.

## Docker Runtime Flags (Important)

Even though Chromium is launched with `--disable-dev-shm-usage` and tmp/cache is under `.artifacts`, add these for robustness:
- Shared memory: `--shm-size=1g` (or `--ipc=host`) to stabilize heavy pages.
- File descriptors: `--ulimit nofile=8192:8192` to avoid FD limits when many tabs/contexts are open.
- Persist profile/data: bind mount `.artifacts`:
  - `-v <host>/.artifacts:/app/surfer-agent/.artifacts`
- In production, avoid publishing CDP (`9222`) publicly; keep it internal to the container network.
- Headful viewer ports (optional): publish `6080` (noVNC) and optionally `5900` (VNC). Restrict with firewall/NSG to admin IPs only.

## Production Compose Override (Headful) — Example

Create `docker-compose.override.yml` (not committed here by default) to harden and constrain prod runs:

```yaml
services:
  surfer-agent:
    environment:
      - HEADFUL=true
      - UVICORN_RELOAD=false
      - WARMUP_ENABLED=true
      - WARMUP_STRICT=false
      - JOBS_MAX_CONCURRENT=2
      - CTX_POOL_MAX=3
      - SURFER_CORS_ORIGINS=https://your-product.example
    shm_size: 1g
    ulimits:
      nofile:
        soft: 8192
        hard: 8192
    # Expose API and (optionally) the headful viewer
    ports:
      - "8001:8001"   # API
      - "6080:6080"   # noVNC (web viewer) — restrict via firewall/NSG
      # - "5900:5900" # VNC (optional; restrict via firewall/NSG)
    # Keep CDP internal (do not publish 9222)
    # volumes persist artifacts/profile
    volumes:
      - ./.artifacts:/app/surfer-agent/.artifacts
```

## Environment & Knobs (Headful defaults)

Core (compose defaults exist; set explicitly in prod):
- `HEADFUL` — true (default). The service runs a headful browser inside the container.
- `UVICORN_RELOAD` — false in prod
- `SURFER_CORS_ORIGINS` — restrict to your product origins
- `LOCALE`, `TIMEZONE` — set for consistent identity/region
- `PROXY_SERVER`, `PROXY_USERNAME`, `PROXY_PASSWORD` — optional for egress control

Logging:
- `SURFER_LOG_LEVEL` — root Python logging level (default `INFO`).
- `SURFER_ECHO_JOB_LOGS` — when `false`, suppresses per‑job stdout/step logs from the container console; detailed logs still write to per‑job files.
- `UVICORN_LOG_LEVEL` — uvicorn server log level (default `info`).
- `UVICORN_ACCESS_LOG` — set to `false` to disable HTTP access logs.

Concurrency & retention:
- `JOBS_MAX_CONCURRENT` (default 2)
- `JOBS_QUEUE_MAX` (default 16)
- `CTX_POOL_MAX` (default 3)
- `JOBS_RESULT_TTL_SEC` (default 900)

Warmup:
- `WARMUP_ENABLED` (default true), `WARMUP_STRICT` (default false), `WARMUP_QUERY` (default “agentic browsing”)

Providers (set via `surfer-agent/.env`):
- Anthropic: `ANTHROPIC_API_KEY`
- OpenAI: `OPENAI_API_KEY`
- Azure OpenAI: `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT_NAME`, `AZURE_OPENAI_API_VERSION`
- OpenRouter: `OPENROUTER_API_KEY`
- Grounding (optional): `MOONDREAM_API_KEY` (or `--moondream-base` if self‑hosting)

## Storage & Artifacts

Artifacts live under `.artifacts` (bind‑mounted in Docker):
- Browser user profile: `.artifacts/pw-user` (persistent cookies/consent)
- CDP info: `.artifacts/ws.json`
- Job DB: `.artifacts/devserver/jobs.sqlite` (durable job index)
- Per‑job folders: `.artifacts/devserver/explorer-<timestamp>/` with `result.json` and `run.log`

Per‑job logging behavior:
- During a run, all stdout/stderr from the Explorer and model traces are captured and written incrementally into `run.log`.
- Container console shows minimal job lifecycle lines only (start/end) when `SURFER_ECHO_JOB_LOGS=false`.

Retention:
- Old `explorer-*` folders pruned, keeping last 20 runs (best‑effort). See code in `surfer-agent/devserver/services.py` (prune on new run).

## Security & Hardening

- Do not expose CDP (`9222`) publicly. Keep only the API port (`8001`) exposed.
- Restrict `SURFER_CORS_ORIGINS` to trusted origins; default `*` is dev‑friendly, not production‑safe.
- Store provider API keys in `surfer-agent/.env`; scope by environment; avoid printing keys in logs.
- Use an Azure NSG to allow inbound `8001` from your product networks only.
- Keep the `.artifacts` volume on an encrypted disk if your compliance posture demands it.

## Health, Observability & Metrics

- Liveness: `GET /healthz` — returns `{ status, services, cdp_url, version }`.
- Jobs lifecycle:
  - `POST /api/explorer` → returns job links (202)
  - `GET /api/jobs/{job_id}` → state: `queued|running|completed|failed|canceled`
  - `GET /api/jobs/{job_id}/logs` → plain text logs
  - `GET /api/jobs/{job_id}/result` → curated result (409 until complete)
- Debug endpoints (limit in prod):
  - `/debug/screenshot`, `/debug/tabs`, `/debug/navigate` (useful during bring‑up)

Server logs include:
- Browser attach and CDP readiness
- Warmup progress and adapter behavior
- Explorer step logs with timing and errors

## Warmup & Debugging Runbook (Headful)

Goal: Ensure the internal browser is healthy, identity is warmed (consent/cookies), and the API can run Explorer jobs.

1) Headful viewer (default):
   - Open the desktop: `http://localhost:6080/vnc_lite.html?host=localhost&port=6080&autoconnect=1&resize=remote`.
   - Accept consents on Google once; the profile persists under `.artifacts/pw-user`.

2) Verify CDP & health:
   - Check `docker logs` for `[entrypoint] Internal CDP is ready.`
   - `curl -s http://127.0.0.1:8001/healthz | jq .` → expect `status:"ok"` and a `ws://` URL in `cdp_url`.

3) Run a quick Explorer job:
   - `curl -s http://127.0.0.1:8001/api/explorer -H 'content-type: application/json' -d '{"instruction":"Research Crawl4AI best practices","headless":false,"max_steps":1}' | jq .`
   - Poll `GET /api/jobs/{job_id}` until `completed`; fetch logs and result.

4) If warmup fails (entrypoint runs `surfer-agent/scripts/warmup.py`):
   - Watch the browser page in noVNC; complete CAPTCHA/consent.
   - Set `LOCALE` / `TIMEZONE` and optionally `PROXY_SERVER` for consistent egress.
   - Keep `WARMUP_STRICT=false` to avoid startup aborts in staging; enable it later if desired.

Common symptoms & fixes:
- X server not ready (headful): entrypoint waits for Xvfb; retry or give the VM a few more seconds.
- Profile locks after abrupt stop: the entrypoint/browser service removes `Singleton*`/`DevToolsActivePort` from `.artifacts/pw-user/**` and retries the launch.
- ENOSPC during temp/cache: temp dirs are under `.artifacts`; ensure the host volume has enough free space.
- Google “sorry”/consent loops: use headful once to solve; the cookie persists.

## Operations

- Restart policy: `restart: unless-stopped` in compose (as provided).
- Log rotation: configure Docker daemon log rotation to avoid disk bloat on the VM.
- Backups: snapshot or rsync `.artifacts/devserver/jobs.sqlite` and selected `explorer-*` folders if you need to preserve job history; otherwise rely on retention.
- Upgrades: rebuild the image (`docker compose build --no-cache`) to refresh Patchright/Chromium and Python deps.

## Minimal Production Checklist

- VM sized to expected concurrency (see tiers above)
- Compose override with `HEADFUL=true`, `UVICORN_RELOAD=false`, `JOBS_MAX_CONCURRENT`/`CTX_POOL_MAX` set
- `--shm-size=1g`, `--ulimit nofile=8192`
- `.artifacts` mounted on persistent disk with enough space
- CORS restricted; CDP not publicly exposed
- Provider keys set in `surfer-agent/.env`
- Health endpoint returns OK; sample Explorer job completes

---

If you need a tailored override file or an Azure provisioning script aligned to your concurrency and regions, we can add those next.
