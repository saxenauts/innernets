-- Migration: 0002_scheduler
-- Purpose: Scheduler tables (schedules, jobs, runs) with RLS and indexes

begin;

-- Extensions (UUID generation)
create extension if not exists pgcrypto;

-- Schedules
create table if not exists public.schedules (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  name text not null,
  cadence text not null, -- cron expression or interval string (e.g., "@hourly" or "PT1H")
  time_zone text not null default 'UTC',
  active boolean not null default true,
  next_run_at timestamptz not null default now(),
  last_enqueued_at timestamptz null,
  meta jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

comment on table public.schedules is 'User-owned schedules defining cadence and state.';

-- Jobs
create table if not exists public.jobs (
  id uuid primary key default gen_random_uuid(),
  schedule_id uuid null references public.schedules(id) on delete set null,
  user_id uuid not null references auth.users(id) on delete cascade,
  idempotency_key text null unique,
  status text not null default 'queued', -- queued|running|succeeded|failed|canceled
  attempts int not null default 0,
  max_attempts int not null default 3,
  queued_at timestamptz not null default now(),
  started_at timestamptz null,
  finished_at timestamptz null,
  payload jsonb not null default '{}'::jsonb,
  last_error jsonb null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

comment on table public.jobs is 'Enqueued work derived from schedules or ad-hoc, per user.';

-- Runs (one job may have one run; allow multiple if we ever re-run)
create table if not exists public.runs (
  id uuid primary key default gen_random_uuid(),
  job_id uuid not null references public.jobs(id) on delete cascade,
  status text not null default 'running', -- running|succeeded|failed|canceled
  started_at timestamptz not null default now(),
  finished_at timestamptz null,
  metrics jsonb not null default '{}'::jsonb,
  error jsonb null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

comment on table public.runs is 'Execution records (metrics, errors) for jobs.';

-- Updated-at trigger (shared)
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_schedules_set_updated_at on public.schedules;
create trigger trg_schedules_set_updated_at
before update on public.schedules
for each row execute procedure public.set_updated_at();

drop trigger if exists trg_jobs_set_updated_at on public.jobs;
create trigger trg_jobs_set_updated_at
before update on public.jobs
for each row execute procedure public.set_updated_at();

drop trigger if exists trg_runs_set_updated_at on public.runs;
create trigger trg_runs_set_updated_at
before update on public.runs
for each row execute procedure public.set_updated_at();

-- Indexes
create index if not exists idx_schedules_next_run on public.schedules (next_run_at) where active = true;
create index if not exists idx_jobs_status_created on public.jobs (status, created_at);
create index if not exists idx_jobs_user on public.jobs (user_id);
create index if not exists idx_runs_job on public.runs (job_id);

-- RLS enable
alter table public.schedules enable row level security;
alter table public.jobs enable row level security;
alter table public.runs enable row level security;

-- Policies: allow users to manage their own schedules/jobs; runs readable by owner
drop policy if exists schedules_owner_rw on public.schedules;
create policy schedules_owner_rw on public.schedules
for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists jobs_owner_rw on public.jobs;
create policy jobs_owner_rw on public.jobs
for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists runs_owner_r on public.runs;
create policy runs_owner_r on public.runs
for select using (
  exists (
    select 1 from public.jobs j where j.id = runs.job_id and j.user_id = auth.uid()
  )
);

-- Grants for API roles (supabase)
grant select, insert, update, delete on table public.schedules to authenticated;
grant select, insert, update, delete on table public.jobs to authenticated;
grant select on table public.runs to authenticated;

commit;

