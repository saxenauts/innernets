-- Migration: 0004_curation_body_md
-- Purpose: Add body_md column to curation_clusters for rich markdown content

begin;

alter table if exists public.curation_clusters
  add column if not exists body_md text null;

commit;

