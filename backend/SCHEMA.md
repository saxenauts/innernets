# Backend Schema (Evolving)

This document tracks the evolving database schema. We use Supabase (Postgres). Keep this human-readable and minimal; migrations live under `backend/migrations/`.

Guidelines
- Start minimal; evolve only when needed by a concrete feature.
- Treat Supabase Auth as the source of truth for users.
- Use UUIDs for primary keys. Use `created_at`/`updated_at` with default `now()`.
- Avoid storing secrets directly; if unavoidable for user connectors, require encryption and access controls.

Entities (current minimal)
- profiles
  - id: uuid (PK, references auth.users.id)
  - display_name: text (nullable)
  - time_zone: text (default 'UTC')
  - meta: jsonb (default '{}')
  - created_at: timestamptz (default now())
  - updated_at: timestamptz (default now())

Notes
- Auth: use Supabase Auth tables; do not duplicate user credentials.
- Secrets: store provider keys outside DB.
- Migrations: keep SQL migrations under `backend/migrations/` and keep this doc in sync.

Change Log
- 2025-08-26 — Minimalized schema to `profiles` only; added migration 0001.
