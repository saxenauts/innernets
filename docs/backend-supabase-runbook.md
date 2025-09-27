# Supabase Runbook — Dev/Prod Schema & Migrations

Goal
- Keep schema changes minimal, reviewed, and reproducible.
- Use a single source of truth for schema: committed SQL migrations.

Setup
- Install Supabase CLI: `brew install supabase/tap/supabase`
- Login: `supabase login` (opens a browser)
- Find your project ref: Supabase Dashboard → Settings → General → Project Reference (e.g., `abcd1234`)
- Find JWT secret: Supabase Dashboard → Settings → API → JWT secret. Put this in `backend/.env` as `SUPABASE_JWT_SECRET`.
  - Supabase access tokens include `aud: "authenticated"`. Backend validates audience by default (`SUPABASE_JWT_AUD`, default `authenticated`).
 - Copy anon key: Supabase Dashboard → Settings → API → anon public key. Put this in `backend/.env` as `SUPABASE_ANON_KEY`.

Link a Project (Dev)
- From the repo root or `backend/`:
  - `supabase link --project-ref <DEV_PROJECT_REF>`
  - This stores link info locally. It does not change the database.

Migration Workflow (minimalist)
1) Author migration SQL in this repo under `backend/migrations/`.
2) Apply to Dev:
   - Easiest: open Supabase Dashboard → SQL Editor → paste the migration SQL and run.
   - Alternative (when CLI remote push is available in your environment):
     - Ensure you’re linked to dev: `supabase link --project-ref <DEV_PROJECT_REF>`
     - Run: `supabase db push` (note: historically local-only; prefer SQL Editor if remote push isn’t enabled)
3) Verify in Dev:
   - Table Editor → confirm table exists
   - Run a simple insert/select in SQL Editor to validate constraints
4) Commit migration SQL file and update `docs/backend-schema.md` (evolving doc)
5) Promote to Prod later:
   - Link prod: `supabase link --project-ref <PROD_PROJECT_REF>`
   - Apply the exact same SQL via SQL Editor or CLI

Testing in Supabase (Dev)
- Create/locate a test user: Dashboard → Authentication → Users → copy the user UUID
- Insert a profile record (service role bypasses RLS in server-side contexts; SQL Editor runs as a superuser):
```
insert into public.profiles (id, display_name)
values ('<AUTH_USER_UUID>', 'Test User')
on conflict (id) do update set display_name = excluded.display_name;
```
- Query back:
```
select id, display_name, time_zone, created_at, updated_at from public.profiles where id = '<AUTH_USER_UUID>';
```
- Note: RLS policies are enforced by the API (auth/anon roles). SQL Editor bypasses RLS. We’ll validate RLS via the backend API once endpoints are added.

Streams, URL Registry, and Curations (0003)
- Apply migration `backend/migrations/2025-08-29_0003_streams_curations_urls.sql` in dev.
- Quick checks:
  - Insert a row into `urls` via the SQL editor, then select it with an `authenticated` session to confirm read access.
  - Create a `streams` row for your test user (or use the API as described below) and verify you cannot see another user’s streams.
  - Create a `curation_runs` row (pointing to your stream) and verify clusters/links enforce ownership via joins.

Backend API checks (dev)
- With a valid Supabase access token (from the test user):
  - `POST /streams` → create a stream (also creates a schedule).
  - `POST /streams/{id}/run` → returns 202 with `{ job_id, status: 'queued' }`.
  - Once the background loop processes the job, `GET /streams/{id}/latest` should return a run with curations and resolved links.

Testing the Backend with JWT + RLS
- Obtain a Supabase access token (e.g., from your frontend session or using `supabase.auth.signInWithPassword`).
- Ensure `backend/.env` has `SUPABASE_JWT_SECRET` set.
- Optionally set `SUPABASE_JWT_AUD` (default `authenticated`).
- Start the API: `cd backend && poetry run uvicorn app.main:app --reload`.
- Call:
  - `PUT /me/profile` with header `Authorization: Bearer <access_token>` and a JSON body like `{ "display_name": "You", "time_zone": "UTC" }`.
  - `GET /me/profile` with the same header; you should see your profile.
  - If you start from repo root, set `DOTENV_PATH=backend/.env` so the server loads the correct `.env`.
 - RLS check: try a different user's token; access should return 404 due to RLS.

Policies & RLS
- Minimal RLS is set in the migration to allow users to select/insert/update their own row only (auth.uid() = id).
- Service role key (used by backend) bypasses RLS by design; do not expose it to the frontend.

Dev/Prod Separation
- Use separate Supabase projects for dev and prod.
- Apply the same committed migration SQL to both (dev first, then prod once validated).

Rollback Strategy (simple)
- Keep each migration small and reversible.
- If a change causes issues in dev, create a new migration to undo rather than editing history.

FAQ
- Where do migrations live? `backend/migrations/`
- Can I change schema via the UI? Yes for dev experiments, but capture the diff as SQL and commit it here.
- What about seed data? Add seed scripts under `backend/migrations/seeds/` as needed.

Curations Markdown Body (0004)
- Apply migration `backend/migrations/2025-09-25_0004_curation_body_md.sql` to add `body_md` to `curation_clusters`.
- After applying, the API will begin returning `body_md` fields in `GET /streams/:id/latest` and `GET /streams/:id/runs`.
- Existing runs will have `body_md = null`; new runs will populate it via the remixer.

