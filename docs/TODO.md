# TODO — Succinct Checklist

- [ ] Backend: unify PostgREST client + retries (shared httpx client, 1x retry, map upstream failures to 503)
- [ ] Backend: typed error model for PostgREST errors (`{code,message}` up the stack)
- [ ] Backend: Surfer health gate (probe `/healthz`, short backoff, fail fast with 503 when down)
- [ ] Backend: finalizer runner (standalone entry) + light backoff + basic metrics
- [ ] Backend: atomic job claiming for workers; queue depth/success/fail counters
- [ ] Agent: add a content index to the main AI agent (index curations/links for retrieval)
- [ ] Frontend: error UX (distinct 401 vs 5xx banners)
- [ ] Frontend: pause polling when tab hidden; resume with catch‑up fetch
- [ ] Frontend: optional preemptive session refresh + single retry on 401
- [ ] Frontend: accessibility pass (dialogs focus, roles, links)
- [ ] Frontend: Stream creation chat (guided onboarding; minimal scaffold)
- [ ] Docs: troubleshooting (CORS/env/401), markdownlint + prettier hygiene
- [ ] CI: backend pytest, frontend vitest, docs lint (markdownlint/prettier)
- [ ] Naming: standardize `sources_hints` → `sources` across APIs/docs
- [ ] Security: re‑audit secrets; document rotation and least‑privilege keys

Note: Cached per‑token Supabase client + 1x retry on Streams reads is already in place; these items are follow‑ups for robustness and polish.
