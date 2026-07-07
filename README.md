# InnerNets

An autonomous content engine. You set up "streams" on a schedule — the system deploys an AI agent that explores the web, searches, reads, and synthesizes findings into curated markdown briefings. Your computer goes out and gathers the world for you.

Built around a simple thesis: **a personal computer shouldn't just hold your thoughts — it should go out and gather knowledge on your behalf.**

## What It Does

InnerNets runs scheduled research cycles called **Streams**. Each stream has:

- A **cadence** (how often it runs — daily, weekly, etc.)
- A **prompt** (what it should explore)
- An **agent** that executes the search-and-synthesize loop

When a stream fires, the agent:
1. Explores the web using Exa search (or the in-process "Surfer" browser agent)
2. Reads and synthesizes what it finds
3. Produces a markdown briefing (`body_md` + source links)
4. Persists it as a "curation" that the frontend renders

The frontend shows your streams, their schedules, and the curated briefings — a personal intelligence feed that updates itself.

## Architecture

```
innernets/
├── frontend/    # Vite + React (TypeScript)
├── backend/     # FastAPI (Python) — API, scheduler, worker, agents
├── docs/        # Architecture, API, schema, and runbook docs
└── compose.*.yml  # Docker configs for local/staging
```

### Backend
- **FastAPI** app with a built-in scheduler and worker
- **Streams** — user-configured research pipelines with per-user cadence
- **Runs** — individual executions of a stream, persisted as curations
- **Agent layer** — in-process AI surfer that explores, searches, and synthesizes
- **Exa API** integration for search
- **Supabase** for auth (JWT with audience validation) and data
- **LLM adapter** supporting multiple providers (Azure OpenAI, OpenAI)

### Frontend
- **Vite + React + TypeScript**
- Renders markdown briefings from stream runs
- Stream management UI (create, schedule, view)
- Supabase auth integration

### Deployment
- Dockerized with staging and local compose configs
- CI/CD pipeline (GitHub Actions) deploying to Azure VM via SSH
- Nginx reverse proxy with TLS

## Quick Start

```bash
git clone https://github.com/saxenauts/innernets.git
cd innernets

# Backend
cd backend
cp .env.example .env  # Fill in Supabase + LLM provider credentials
pip install -e .  # or use the venv
uvicorn src.app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Frontend at `localhost:5173`, API at `localhost:8000`.

## Documentation

The `docs/` directory covers architecture, API specs, schemas, and operational runbooks:

- [`docs/architecture-runs-scheduler.md`](docs/architecture-runs-scheduler.md) — core architecture
- [`docs/search-loop.md`](docs/search-loop.md) — how the agent search loop works
- [`docs/backend-llm-adapter.md`](docs/backend-llm-adapter.md) — multi-provider LLM setup
- [`docs/integration.md`](docs/integration.md) — frontend ↔ backend contract

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, Python, APScheduler (in-process), async |
| Frontend | Vite, React, TypeScript |
| Database | Supabase (PostgreSQL) |
| AI | Azure OpenAI / OpenAI (multi-provider adapter) |
| Search | Exa API |
| Auth | Supabase JWT (audience-validated) |
| Deploy | Docker, GitHub Actions → Azure VM, Nginx |

## Context

Built August–October 2025. This extends the thesis from [Kaleidos](https://github.com/saxenauts/kaleidos) (organizing internal thinking) outward — the personal computer autonomously gathering and synthesizing external knowledge. The same thread continues in [Syke](https://github.com/saxenauts/syke) (ambient memory across all your tools).

## License

MIT
