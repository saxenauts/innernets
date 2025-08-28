# Backend Schema (Evolving)

This document tracks the evolving database schema. We use Supabase (Postgres). Keep this human-readable and minimal; migrations live under `backend/migrations/`.

Guidelines
- Start minimal; evolve only when needed by a concrete feature.
- Treat Supabase Auth as the source of truth for users.
- Use UUIDs for primary keys. Use `created_at`/`updated_at` with default `now()`.
- Avoid storing secrets directly; if unavoidable for user connectors, require encryption and access controls.

Entities

- profiles
  - id: uuid (PK, references auth.users.id)
  - display_name: text (nullable)
  - time_zone: text (default 'UTC')
  - meta: jsonb (default '{}')
  - created_at: timestamptz (default now())
  - updated_at: timestamptz (default now())

- streams
  - id: uuid (PK)
  - user_id: uuid (FK auth.users.id)
  - mission: text
  - sources_hints: text (nullable)
  - cadence: text (e.g., daily|3xweek|weekly|discovery|cron)
  - time_zone: text (default 'UTC')
  - active: boolean (default true)
  - meta: jsonb (default '{}')
  - created_at/updated_at: timestamptz

- urls (registry)
  - id: uuid (PK)
  - url: text (unique)
  - domain: text
  - last_title: text (nullable)
  - last_description: text (nullable)
  - last_published_at: timestamptz (nullable)
  - first_seen_at/last_seen_at: timestamptz
  - meta: jsonb (default '{}')

- curation_runs
  - id: uuid (PK)
  - stream_id: uuid (FK streams.id)
  - job_id: uuid (FK jobs.id, nullable)
  - status: text (running|succeeded|failed|canceled)
  - started_at/finished_at: timestamptz
  - metrics: jsonb (default '{}')
  - raw: jsonb (nullable)

- curation_clusters
  - id: uuid (PK)
  - run_id: uuid (FK curation_runs.id)
  - title: text
  - hook: text
  - position: int

- curation_cluster_links
  - id: uuid (PK)
  - cluster_id: uuid (FK curation_clusters.id)
  - url_id: uuid (FK urls.id)
  - snapshot_title: text (nullable)
  - position: int

Notes
- Auth: use Supabase Auth tables; do not duplicate user credentials.
- Secrets: store provider keys outside DB.
- Migrations: keep SQL migrations under `backend/migrations/` and keep this doc in sync.

Change Log
- 2025-08-26 — Minimalized schema to `profiles` only; added migration 0001.
- 2025-08-29 — Added streams, urls registry, and curations tables; migration 0003.
