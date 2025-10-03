# Staging, Dev, and Prod Playbook (Minimal)

This is the simplified, minimal path to get dev and staging cleanly separated now, with a light path to prod later.

Related docs:
- Backend env/runbook: `docs/backend-environment.md`, `docs/backend-supabase-runbook.md`
- Surfer: `docs/surfer-docker-integration.md`, `docs/surfer-docker-production.md`

## Chosen Staging VM
- Azure `Standard_D4as_v5` — 4 vCPU, 16 GiB RAM (Ubuntu 22.04 LTS)
- Why: Stable CPU (non‑burstable) and enough headroom for 2 concurrent Surfer jobs plus API/worker without contention. Keeps staging responsive for external testers.
- Disks (chosen):
  - OS: Standard SSD 64 GiB
  - Data: Premium SSD 256 GiB for Surfer `.artifacts` and logs
- Networking: Enable Accelerated Networking if available; expose only 80/443 (NSG), keep 8000/8001 private.
- Cost‑savvy alternative later: `Standard_D2as_v5` (2 vCPU, 8 GiB) if you cap Surfer to 1 concurrent job and accept tighter headroom.

## Environments & Domains
- Dev (local)
  - Frontend: `http://localhost:5173`
  - Backend: `http://localhost:8000`
  - DB: current Supabase project (shared with staging)
  - Surfer: optional local; not required for most frontend flows

- Staging
  - Frontend: `https://staging.innernets.ai` (Vercel)
  - Backend API: `https://api-staging.innernets.ai` (Azure VM)
  - Surfer: runs on the same Azure VM, private on port `8001` (no public exposure)

- Prod (later)
  - TODO after staging is stable (separate Supabase, domains, approvals)

## Branching
- Work on feature branches; open PRs.
- Merge to `main` = deploy to staging.
- Prod promotion plan can be added later (tags or protected branch).

## Frontend Deploy (Vercel)
- Vercel Git integration (what it is): connect this GitHub repo in Vercel; every push builds and deploys.
  - PRs get “Preview” URLs automatically for review.
  - Map `staging.innernets.ai` to the deployment produced from `main`.
  - Configure env vars per Vercel scope (Development, Preview, Production).
- If you prefer GitHub-only CI, we can use the `vercel` CLI in Actions later, but Git integration is simplest now.

## Backend Deploy (Azure VM, build in place)
- One-time VM setup
  - Install Docker and Compose v2.
  - Clone this repo on the VM (e.g., `/opt/innernets`).
  - Create `backend/.env.staging` on the VM with the staging secrets (don’t commit it).
  - Set up Nginx or Caddy on the VM to serve `api-staging.innernets.ai` over HTTPS and proxy to `http://127.0.0.1:8000`.
  - Run Surfer (from its separate repo) via its own `docker compose` and expose port `8001` locally only.

- Compose file (minimal sketch, builds locally on VM)
```yaml
# compose.staging.yml (committed at repo root)
services:
  api:
    build: ./backend
    env_file:
      - backend/.env.staging
    restart: unless-stopped
    ports:
      - "127.0.0.1:8000:8000"  # private; Nginx proxies external HTTPS to this
    extra_hosts:
      - "host.docker.internal:host-gateway"  # API container can call Surfer on the host (127.0.0.1:8001)

  worker:
    build: ./backend
    env_file:
      - backend/.env.staging
    command: ["python", "-m", "app.scheduler.worker_main"]
    restart: unless-stopped
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

- Start/Update on VM
```
cd /opt/innernets
git pull
docker compose -f compose.staging.yml -p innernets-staging up -d --build
```

- CI (minimal, later): a GitHub Action can SSH to the VM on pushes to `main` and run the two commands above. No image registry needed for now. Registry is a TODO.
  - Added: `.github/workflows/deploy-staging.yml` uses SSH (appleboy/ssh-action) to run `git pull` and `docker compose up -d --build`.

## Surfer Connectivity (private on 8001)
- Keep Surfer running separately on the VM; expose `8001` locally only.
- Set backend `SURFER_BASE_URL=http://host.docker.internal:8001` in `backend/.env.staging` so the API container can reach the host’s Surfer service.
- Health check before starting the worker: `curl -s http://127.0.0.1:8001/healthz | jq .`.

Surfer CI/deploy strategy:
- We deploy Surfer from its own repository with a similar SSH workflow (clone/pull + `docker compose up -d --build`).
- This repo’s CI will not update Surfer (leave `SURFER_WORKDIR` unset).

## Supabase (dev + staging shared for now)
- Using one Supabase for both is fine to start.
- “Gating migrations” explained simply: don’t auto-apply schema migrations on every deploy. Run them only when you intend to change the shared DB.
  - For now, apply SQL files manually when needed from the VM or your laptop:
    - Ensure `POSTGRES_CONNECTION_STRING` is set (see `docs/backend-environment.md`).
    - Example: `psql "$POSTGRES_CONNECTION_STRING" -f backend/migrations/2025-09-27_0005_runs_job_id_unique.sql`.
- Day-to-day development can use your test user accounts and data; staging will see the same DB.

## Nginx (reverse proxy)
- On the VM, install Nginx and Certbot.
- Create a server block for `api-staging.innernets.ai` that proxies to `http://127.0.0.1:8000` and enables TLS via Let’s Encrypt.
- Example config: `docs/nginx-api-staging.conf.example`.

## DNS & TLS (quick)
- `staging.innernets.ai` → Vercel (CNAME).
- `api-staging.innernets.ai` → A record to the VM.
- VM runs Nginx/Caddy to terminate TLS and reverse proxy to `localhost:8000`.

## TODO (later)
- Container registry (GHCR/ACR) and image-based deploys.
- GitHub Action that deploys backend automatically on push to `main` (SSH workflow).
- Separate Dev Supabase; Prod Supabase cloned from staging at first production cut.
- Observability (logs, metrics) and a rollback note.

## Files added in repo for staging
- `compose.staging.yml` — builds and runs API + worker; private port binding.
- `backend/Dockerfile` — Poetry-based Python image for API and worker.
- `backend/.dockerignore` — keeps image small and excludes secrets/tests.
- `.github/workflows/deploy-staging.yml` — SSH-based deploy from GitHub Actions on push to `main`.

## Git Access (PAT credential store)
- Create a Fine‑Grained PAT: repo access → select this repo (and Surfer repo), permissions: Contents: Read; Metadata: Read; set an expiry.
- Configure one‑time on the VM: `git config --global credential.helper store`
- Clone via HTTPS (first time prompts for username + PAT):
  - `mkdir -p ~/apps && cd ~/apps`
  - `git clone https://github.com/<org>/innernets.git`
  - `git clone https://github.com/<org>/<surfer-repo>.git surfer-agent`
- Git saves token in `~/.git-credentials` so future `git pull` is non‑interactive. Tighten perms: `chmod 600 ~/.git-credentials`.
- Set GitHub Action secret `STAGING_WORKDIR` to your actual path (e.g., `/home/<user>/apps/innernets`).

## Backend Docker bring‑up (commands)
- Prepare env: `cp backend/.env.example.staging backend/.env.staging` and fill values.
  - Ensure: `CORS_ALLOW_ORIGINS=https://staging.innernets.ai`, `SURFER_BASE_URL=http://host.docker.internal:8001`, Supabase vars, provider keys.
- Build & run: `docker compose -f compose.staging.yml -p innernets-staging up -d --build`
- Verify: `curl -s http://127.0.0.1:8000/healthz | jq .` (expect `{ ok: true, surfer_ok: true }`).

## Surfer Docker bring‑up (commands)
- In your Surfer repo path (e.g., `~/apps/surfer-agent`):
  - Create `.env` with provider keys and `SURFER_CORS_ORIGINS=https://staging.innernets.ai`.
  - Ensure compose binds private port and adequate SHM. Minimal example:
```
services:
  surfer:
    build: .
    env_file: .env
    ports:
      - "127.0.0.1:8001:8001"
    shm_size: "1g"
    volumes:
      - ./.artifacts:/app/surfer-agent/.artifacts
    restart: unless-stopped
```
- Start: `docker compose up -d`
- Verify: `curl -s http://127.0.0.1:8001/healthz | jq .`

## Optional: Local Docker Test (before VM) — Status: Done

This mirrors staging but runs everything on your machine so you can keep using `npm run dev` for the frontend.

Steps
- [x] Create a local backend env file from example:
  - [x] `cp backend/.env.example.local.docker backend/.env.local.docker` and fill Supabase vars.
  - [x] Point `SURFER_BASE_URL` at your local Surfer service (e.g., `http://host.docker.internal:8001`). Explorer now runs inside the worker, so the external service only needs to expose `/api/google-search` and `/api/read-wave`.
- [x] Start backend containers (api + worker):
  - [x] `docker compose -f compose.local.yml -p innernets-local up -d --build`
- [x] Frontend dev:
  - [x] Ensure `frontend/.env.local` has `VITE_API_BASE_URL=http://localhost:8000` (default in `.env.example`).
  - [x] `cd frontend && npm run dev` → open http://localhost:5173.
- [x] Health checks:
  - [x] `curl -s http://localhost:8000/healthz | jq .` (ok true; surfer_ok true if mock or local Surfer works)
- [x] Stop local stack (optional when done testing):
  - [x] `docker compose -f compose.local.yml -p innernets-local down`

## Staging Bring-up Checklist

- [ ] Azure VM (Ubuntu) + Networking
  - [x] VM: Ubuntu 22.04 LTS, static public IP, SSH key auth
  - [ ] NSG: allow TCP 22 (restricted), 80, 443; keep 8000/8001 closed
  - [x] Base setup: update/upgrade, Docker/Compose installed, tools installed, timezone set
    - [x] `sudo apt-get update && sudo apt-get upgrade -y`
    - [x] `curl -fsSL https://get.docker.com | sh` then `sudo usermod -aG docker $USER`
    - [x] `sudo apt-get install -y git nginx python3-certbot-nginx jq`
    - [x] `sudo timedatectl set-timezone UTC`

- [x] Surfer (private on 8001)
  - [x] Clone Surfer to host (e.g., `~/apps/surfer-agent`)
  - [x] `.env` with provider keys, `SURFER_CORS_ORIGINS=https://staging.innernets.ai`
  - [x] Compose binds `127.0.0.1:8001:8001` and sets `shm_size: "1g"`
  - [x] Health OK: `curl -s http://127.0.0.1:8001/healthz | jq .`

- [x] Clone this repo on VM
  - [x] Cloned via HTTPS using PAT + credential store to your home path (e.g., `/home/<user>/apps/innernets`)
  - [ ] Set `STAGING_WORKDIR` repo secret to this path (for the deploy Action)

- [x] Backend env (staging)
  - [x] Created `backend/.env.staging` and filled Supabase vars and provider keys
  - [x] Set `CORS_ALLOW_ORIGINS=https://staging.innernets.ai`
  - [x] Set `SURFER_BASE_URL=http://host.docker.internal:8001`
  - [x] Ensured `SCHEDULER_IN_APP=0`

- [x] Backend containers (Compose)
  - [x] `docker compose -f compose.staging.yml -p innernets-staging up -d --build`
  - [x] Health OK: `curl -s http://127.0.0.1:8000/healthz | jq .`

- [x] Vercel (frontend project)
  - [x] Import GitHub repo in Vercel; set Root Directory to `frontend/`
  - [x] Confirm Framework auto-detects Vite; Output Directory `dist`
  - [x] Set Environment Variables (Production scope):
    - [x] `VITE_API_BASE_URL=https://api-staging.innernets.ai`
    - [x] `VITE_SUPABASE_URL=<your supabase url>`
    - [x] `VITE_SUPABASE_ANON_KEY=<your anon key>`
  - [x] Trigger the first build/deploy (will deploy to a `*.vercel.app` URL)
  - [x] Add `staging.innernets.ai` under Project → Settings → Domains (will show a CNAME target to create in DNS)

- [x] DNS (Cloudflare)
  - [x] For `staging.innernets.ai` (Frontend via Vercel)
    - [x] Create a `CNAME` record: Name `staging` → Target the value shown by Vercel (e.g., `cname.vercel-dns.com`)
    - [x] Proxy status: DNS only (grey cloud)
    - [x] Verified in Vercel as Configured
  - [x] For `api-staging.innernets.ai` (Backend on VM)
    - [x] Create an `A` record: Name `api-staging` → Value `<VM Public IP>`, TTL 300s
    - [x] Proxy status: DNS only (grey cloud) during Let’s Encrypt issuance
    - [x] Validated via `dig +short api-staging.innernets.ai`
  - [ ] Cloudflare SSL/TLS
    - [ ] Set SSL/TLS mode to “Full” (or “Full (strict)” once origin certs are valid)
    - [ ] Leave “Always Use HTTPS” off; Nginx/Vercel handle redirects and certs

- [x] Nginx + TLS for API
  - [x] Configure server block per `docs/nginx-api-staging.conf.example` (HTTP-only first)
  - [x] `sudo nginx -t && sudo systemctl reload nginx`
  - [x] `sudo certbot --nginx -d api-staging.innernets.ai --redirect`

- [x] GitHub Actions deploy (SSH)
  - [x] Add secrets: `STAGING_SSH_HOST`, `STAGING_SSH_USER`, `STAGING_SSH_PASSWORD`, `STAGING_WORKDIR=/home/<user>/apps/innernets`
  - [x] Push to `main` triggers `.github/workflows/deploy-staging.yml` (with retrying health check)

- [x] Smoke tests
  - [x] Surfer: `curl -s http://127.0.0.1:8001/healthz | jq .`
  - [x] Backend: `curl -s https://api-staging.innernets.ai/healthz | jq .`
  - [x] Frontend: login, create Stream, Run Now → see curation

- [ ] Operations
  - [ ] DB migrations: run intentionally via `psql` with `POSTGRES_CONNECTION_STRING`
  - [ ] Rollback: checkout previous commit and rebuild via compose
  - [ ] Security: keep 8001 private; restrict SSH to trusted IPs
