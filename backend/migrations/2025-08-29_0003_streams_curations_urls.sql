-- Migration: 0003_streams_curations_urls
-- Purpose: Streams, URL registry, and curation storage with RLS

begin;

-- Ensure helper function exists
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- STREAMS
create table if not exists public.streams (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  mission text not null,
  sources_hints text null,
  cadence text not null,
  time_zone text not null default 'UTC',
  active boolean not null default true,
  meta jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

drop trigger if exists trg_streams_set_updated_at on public.streams;
create trigger trg_streams_set_updated_at
before update on public.streams
for each row execute procedure public.set_updated_at();

alter table public.streams enable row level security;

drop policy if exists streams_owner_rw on public.streams;
create policy streams_owner_rw on public.streams
for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

grant select, insert, update, delete on table public.streams to authenticated;

-- URL REGISTRY
create table if not exists public.urls (
  id uuid primary key default gen_random_uuid(),
  url text not null unique,
  domain text not null,
  last_title text null,
  last_description text null,
  last_published_at timestamptz null,
  first_seen_at timestamptz not null default now(),
  last_seen_at timestamptz not null default now(),
  meta jsonb not null default '{}'::jsonb
);

create index if not exists idx_urls_domain on public.urls (domain);

alter table public.urls enable row level security;

-- Allow authenticated to read URLs; writes are server-side (service role)
drop policy if exists urls_select_all on public.urls;
create policy urls_select_all on public.urls
for select using (true);

grant select on table public.urls to authenticated;

-- CURATION RUNS
create table if not exists public.curation_runs (
  id uuid primary key default gen_random_uuid(),
  stream_id uuid not null references public.streams(id) on delete cascade,
  job_id uuid null references public.jobs(id) on delete set null,
  status text not null default 'running',
  started_at timestamptz not null default now(),
  finished_at timestamptz null,
  metrics jsonb not null default '{}'::jsonb,
  raw jsonb null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_curation_runs_stream_started on public.curation_runs (stream_id, started_at desc);

drop trigger if exists trg_curation_runs_set_updated_at on public.curation_runs;
create trigger trg_curation_runs_set_updated_at
before update on public.curation_runs
for each row execute procedure public.set_updated_at();

alter table public.curation_runs enable row level security;

drop policy if exists curation_runs_owner_rw on public.curation_runs;
create policy curation_runs_owner_rw on public.curation_runs
for all using (
  exists (
    select 1 from public.streams s where s.id = curation_runs.stream_id and s.user_id = auth.uid()
  )
) with check (
  exists (
    select 1 from public.streams s2 where s2.id = curation_runs.stream_id and s2.user_id = auth.uid()
  )
);

grant select, insert, update, delete on table public.curation_runs to authenticated;

-- CURATION CLUSTERS
create table if not exists public.curation_clusters (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references public.curation_runs(id) on delete cascade,
  title text not null,
  hook text not null,
  position int not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_curation_clusters_run_pos on public.curation_clusters (run_id, position);

drop trigger if exists trg_curation_clusters_set_updated_at on public.curation_clusters;
create trigger trg_curation_clusters_set_updated_at
before update on public.curation_clusters
for each row execute procedure public.set_updated_at();

alter table public.curation_clusters enable row level security;

drop policy if exists curation_clusters_owner_rw on public.curation_clusters;
create policy curation_clusters_owner_rw on public.curation_clusters
for all using (
  exists (
    select 1
    from public.curation_runs r
    join public.streams s on s.id = r.stream_id
    where r.id = curation_clusters.run_id and s.user_id = auth.uid()
  )
) with check (
  exists (
    select 1
    from public.curation_runs r2
    join public.streams s2 on s2.id = r2.stream_id
    where r2.id = curation_clusters.run_id and s2.user_id = auth.uid()
  )
);

grant select, insert, update, delete on table public.curation_clusters to authenticated;

-- CURATION CLUSTER LINKS
create table if not exists public.curation_cluster_links (
  id uuid primary key default gen_random_uuid(),
  cluster_id uuid not null references public.curation_clusters(id) on delete cascade,
  url_id uuid not null references public.urls(id) on delete restrict,
  snapshot_title text null,
  position int not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_cluster_links_cluster_pos on public.curation_cluster_links (cluster_id, position);

drop trigger if exists trg_curation_cluster_links_set_updated_at on public.curation_cluster_links;
create trigger trg_curation_cluster_links_set_updated_at
before update on public.curation_cluster_links
for each row execute procedure public.set_updated_at();

alter table public.curation_cluster_links enable row level security;

drop policy if exists curation_cluster_links_owner_rw on public.curation_cluster_links;
create policy curation_cluster_links_owner_rw on public.curation_cluster_links
for all using (
  exists (
    select 1
    from public.curation_clusters c
    join public.curation_runs r on r.id = c.run_id
    join public.streams s on s.id = r.stream_id
    where c.id = curation_cluster_links.cluster_id and s.user_id = auth.uid()
  )
) with check (
  exists (
    select 1
    from public.curation_clusters c2
    join public.curation_runs r2 on r2.id = c2.run_id
    join public.streams s2 on s2.id = r2.stream_id
    where c2.id = curation_cluster_links.cluster_id and s2.user_id = auth.uid()
  )
);

grant select, insert, update, delete on table public.curation_cluster_links to authenticated;

commit;

