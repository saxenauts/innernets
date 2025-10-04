# Search Loops — Canonical Reference

This document summarizes the two exploration loops used in the system and links to their detailed specs.

## Surfer Loop (default)
Purpose: Long-running, browser-based exploration. Yields findings that are remixed into curated markdown bodies.

High-level steps
1. Build prior context (recent Stream runs).
2. LLM drafts a concise exploration instruction and a richer context block.
3. Run the Explorer module in-process. It iterates through search and reading waves locally, calling Surfer’s primitive APIs (`/api/google-search`, `/api/read-wave`) on each step.
4. Receive Explorer findings `{ curations: [{ summary, links[] }] }` plus detailed logs.
5. LLM remixes into output curations with `title`, `body_md`, and explicit `links` (no inline links in the body).
6. Persist `curation_runs`, `curation_clusters`, and `curation_cluster_links`; resolve each link to the URL registry.

Where to read more
- Agent workflow and prompts: `backend/src/app/agents/surfer_workflow.py`, `backend/src/app/llm/prompts_surfer.py`
- Service API: `docs/surfer-docker-service-api.md`
- Integration & architecture: `docs/integration.md`, `docs/architecture-runs-scheduler.md`

## Search-Only Loop (legacy)
Purpose: Lightweight Exa-based search pipeline. Kept for back-compat and experiments.

High-level steps
1. LLM generates 3–5 search queries (keyword/neural).
2. Exa search per query; dedupe; assign short IDs.
3. LLM filters candidates to read (IDs only).
4. Exa contents for selected URLs (text only by default).
5. LLM proposes follow-up queries; search again; continue ID numbering.
6. LLM consolidates curations (title, hook/body, link_ids) and we map IDs back to URLs.

Where to read more
- Plan and pricing: `docs/search-only-plan.md`
- Agent and steps: `backend/src/app/agents/search_workflow.py`, `backend/src/app/llm/search_steps.py`
- Architecture context: `docs/architecture-runs-scheduler.md`
