-- Ensure each job can create at most one run
do $$
begin
    if not exists (
        select 1 from pg_indexes where schemaname = 'public' and indexname = 'runs_job_id_unique'
    ) then
        execute 'create unique index runs_job_id_unique on public.runs (job_id)';
    end if;
end $$;

