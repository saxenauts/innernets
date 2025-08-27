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
4) Commit migration SQL file and update `backend/SCHEMA.md` (evolving doc)
5) Promote to Prod later:
   - Link prod: `supabase link --project-ref <PROD_PROJECT_REF>`
   - Apply the exact same SQL via SQL Editor or CLI

Testing in Supabase (Dev)
- Create/locate a test user: Dashboard → Authentication → Users → copy the user UUID
- Insert a profile record (service role bypasses RLS in server-side contexts; SQL Editor runs as a superuser):
```sql
insert into public.profiles (id, display_name)
values ('<AUTH_USER_UUID>', 'Test User')
on conflict (id) do update set display_name = excluded.display_name;
```
- Query back:
```sql
select id, display_name, time_zone, created_at, updated_at from public.profiles where id = '<AUTH_USER_UUID>';
```
- Note: RLS policies are enforced by the API (auth/anon roles). SQL Editor bypasses RLS. We’ll validate RLS via the backend API once endpoints are added.

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
