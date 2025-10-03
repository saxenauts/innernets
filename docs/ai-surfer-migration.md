AI Surfer → InnerNets Migration Log
=================================

Status Snapshot
---------------
- InnerNets branch: `surfer-ai-migration`
- Ai-surfer branch: `feature/explorer-readwave-fix` *(renamed from the earlier `feature/decoupling-ai` work branch on 2025-10-03)*
- Objective: move the full Explorer “intelligence” (planner, SERP filter, reading loop, curation) into InnerNets while keeping ai-surfer responsible only for browser/search/markdown primitives.

Chronological Log of Work
-------------------------

1. **Initial Planning (doc-only)**
   - Captured desired end state and constraints in this document (original draft).
   - Identified contracts we needed from ai-surfer (`/api/google-search`, `/api/read-wave`) and modules to port (Explorer prompts, models, runner).

2. **InnerNets branch + groundwork**
   - Created `surfer-ai-migration` branch in `innernets`.
   - Added early placeholder module (`app/explorer/engine`) with custom steps; later removed once direct Explorer port was adopted.

3. **Ai-surfer branch setup**
   - Created `feature/decoupling-ai` branch in `ai-surfer` repository to host service changes (renamed later to `feature/explorer-readwave-fix`).

4. **New ai-surfer `/api/read-wave` endpoint**
   - File: `ai-surfer/surfer-agent/devserver/app.py`, `devserver/services.py` (initial version).
   - Implemented wave-based markdown reader returning `{ pages: [...] }` to service multiple URLs per call.

5. **InnerNets “engine” prototype (superseded)**
   - Files introduced (later deleted):
     - `innernets/backend/src/app/explorer/engine/runner.py`
     - `innernets/backend/src/app/explorer/steps/{models.py,prompts.py,steps.py}`
   - Allowed us to test API boundaries but diverged from ai-surfer Explorer behavior.

6. **Logging and scheduler visibility fixes**
   - `innernets/backend/src/app/scheduler/jobs.py`: ensured queued jobs set `status=queued`, `queued_at`, etc.
   - `innernets/backend/src/app/scheduler/worker.py`: INFO logs when jobs are claimed.
   - `.env.local.docker`: set `LOG_LEVEL=info` to tame noisy debug output.

7. **Ai-surfer Google search parity fix**
   - Issue: initial `/api/google-search` used a new harness per call (no Patchright profile), leading to missing SERP activity and flaky results.
   - Fixes:
     - `ai-surfer/surfer-agent/devserver/services.py`: run Google searches through `BrowserManager + JobSession`, sharing a single CDP session just like Explorer.
     - `ai-surfer/surfer-agent/src/adapters/runner_google.py`: when invoked via JobSession, ensure SERP page is foregrounded in the dev browser so we can see it over VNC.
     - Added concise console lines (`[api] google-search … items=N`).

8. **Ai-surfer read-wave JobSession parity**
   - Issue: first `/api/read-wave` implementation spun up transient harnesses, so no observable browser activity and mismatched concurrency.
   - Fix:
     - `devserver/services.py`: refactored `read_wave` to reuse the same `BrowserManager` and create a `JobSession` per API call, matching Explorer’s multi-tab concurrency.
     - Outputs now include `links` extracted from markdown; console emits `[api] read-wave urls=X pages=Y`.

9. **Environment adjustments**
   - `.env.local.docker` in innernets: set `SURFER_HEADLESS=0` so dev runs show full browsing in ai-surfer’s noVNC (mirrors Explorer debugging experience).

10. **Decision: drop custom engine and port Explorer verbatim**
    - Based on testing feedback, we removed the bespoke innernets engine and copied the real Explorer stack to guarantee parity.

11. **Removal of prototype engine code**
    - Deleted directories:
      - `innernets/backend/src/app/explorer/engine`
      - `innernets/backend/src/app/explorer/steps`
    - Ensured no stale imports remain in `surfer_workflow` or elsewhere.

12. **Explorer module ported into InnerNets**
    - New files copied (verbatim unless noted) from `ai-surfer/surfer-agent/src/explorer/`:
      - `innernets/backend/src/app/explorer/__init__.py`
      - `innernets/backend/src/app/explorer/ansi.py` *(relative import updated to stay internal)*
      - `innernets/backend/src/app/explorer/logger.py` *(import path fix only)*
      - `innernets/backend/src/app/explorer/models.py`
      - `innernets/backend/src/app/explorer/prompts.py`
      - `innernets/backend/src/app/explorer/llm.py`
      - `innernets/backend/src/app/explorer/runner.py`
    - Adaptations inside `runner.py`:
      - Replaced direct adapter/browser usage with calls to `app.clients.surfer_client.google_search` and `.read_wave`.
      - Removed `AdapterStore`, `BrowserHarness`, and `SurfCrawler` setup (these stay inside ai-surfer).
      - Added environment fallback to `settings.AZURE_OPENAI_DEPLOYMENT_NAME` when resolving the LLM model.
      - Persisted artifacts under `innernets/.artifacts/innernets-explorer/…`.
      - Maintained original logging sequence (`step_request`, `search_overview`, `reading_batch_request`, etc.) for identical console output.

13. **InnerNets surfer workflow integration**
    - File: `innernets/backend/src/app/agents/surfer_workflow.py`.
      - Generates the Explorer `instruction` as before (same `surfer_steps.generate_instruction`).
      - Creates per-run artifact directory via `_make_artifacts_dir(job_id)`.
      - Instantiates the new `Explorer` with settings-driven knobs (`SURFER_MAX_STEPS`, `SURFER_BATCH_SIZE`, `SURFER_SEARCH_CONCURRENCY`, etc.).
      - Logs instruction/context through `Explorer.logger` so the first frames mirror ai-surfer Explorer logs.
      - Calls `Explorer.run()` instead of `/api/explorer`.
      - Converts `curations_batches` into the structure expected by the remix step, then persists metrics (including `explorer_confidence` and artifact path).

14. **Surfer client adjustments**
    - `innernets/backend/src/app/clients/surfer_client.py` already contained `google_search`/`read_wave`; ensured they align with new usage (no changes required during final port, but kept for reference).

15. **Testing helpers**
    - Verified artifact path helper inside poetry venv (`poetry run python -m app.agents…`) to ensure no import regressions.

Key Endpoints & Contracts (Current State)
-----------------------------------------

Ai-surfer devserver (`feature/explorer-readwave-fix`)
- `POST /api/google-search`
  - Body: `{ "query": str, "headless"?: bool }
  - Behavior: runs query via shared JobSession; returns `{ "result": { "items": { "serp": { "items": [...] } } }, "logs": str }`.
  - Implementation: `surfer-agent/devserver/services.py::run_google_search`.

- `POST /api/read-wave`
  - Body: `{ "urls": [str], "headless"?: bool, "citations"?: bool, "prune"?: bool }`
  - Behavior: sequentially schedules Playwright captures inside the existing BrowserManager session; returns `{ "result": { "pages": [{ "url", "content", "references"?, "links"[] }] }, "logs": str }`.
  - Implementation: `surfer-agent/devserver/services.py::read_wave`.

InnerNets backend (`surfer-ai-migration`)
- Explorer lives under `backend/src/app/explorer/` mirroring ai-surfer structure.
- Surfer workflow is now in-process; no calls to `/api/explorer` remain.
- Artifacts (LLM inputs/outputs, memory dumps) are written to `innernets/.artifacts/innernets-explorer/explorer-<timestamp>-<jobid>/`.

Files Added / Removed in InnerNets
----------------------------------

Added:
- `backend/src/app/explorer/__init__.py`
- `backend/src/app/explorer/ansi.py`
- `backend/src/app/explorer/logger.py`
- `backend/src/app/explorer/llm.py`
- `backend/src/app/explorer/models.py`
- `backend/src/app/explorer/prompts.py`
- `backend/src/app/explorer/runner.py`

Removed:
- `backend/src/app/explorer/engine/` (entire directory)
- `backend/src/app/explorer/steps/` (entire directory)

Updated:
- `backend/src/app/agents/surfer_workflow.py`
- `backend/src/app/clients/surfer_client.py` (earlier during migration; no final-day edits)
- `backend/.env.local.docker` (log level + headless defaults)

Outstanding Follow-ups / Notes
------------------------------
- Review documentation across repos that still references `/api/explorer` (e.g., `docs/surfer-docker-integration.md`) and update to mention the new in-process Explorer.
- Consider adding automated tests around `Explorer.run()` with mocked surfer_client to guard against regressions.
- The explorer logger still prints ANSI blocks; ensure deployment environments capture these logs correctly.
- Continue monitoring Google SERP block behaviour; current JobSession implementation surfaces “sorry” responses but may warrant retries.
- 2025-10 regression post-port: `/api/read-wave` deadlocked when invoked by InnerNets because the
  handler ran `ThreadPoolExecutor` futures through `as_completed(...)` on the event loop. Fix merged by
  dispatching `_read_one` via `loop.run_in_executor(...)` and `asyncio.gather(...)` so BrowserManager
  keeps servicing capture calls. Without the fix, Explorer never progressed beyond Step 1.
- Docker rebuilds may fail with “invalid signature” during Ubuntu’s archive rotation. Re-run with a
  clean Docker cache or retry once mirrors sync; the runtime image published in CI already carries the
  refreshed keys.

How to Validate End-to-End
--------------------------
1. **Ai-surfer**
   - `docker compose build --no-cache`
   - `docker compose up -d`
   - Tail logs: `docker compose logs -f --tail=100 surfer-agent`
2. **InnerNets**
   - `docker compose -f compose.local.yml build --no-cache`
   - `docker compose -f compose.local.yml up -d`
   - Tail worker logs: `docker compose -f compose.local.yml logs -f worker`
3. Trigger “Run Now” from the frontend or enqueue a job via Supabase.
   - Expect InnerNets worker logs to show Explorer frames (`Step LLM Request`, `Search (Google)`, `Reading LLM Response`, etc.).
   - Expect ai-surfer logs to show `[api] google-search …` and `[api] read-wave …` plus visible browser activity in noVNC (if `SURFER_HEADLESS=0`).

Change Digest for Next Engineer
-------------------------------
- Explorer logic now resides entirely in InnerNets (`app/explorer/*`), copied from ai-surfer with minimal adjustments.
- Ai-surfer devserver exposes `/api/google-search` and `/api/read-wave` with JobSession parity so InnerNets can rely on the same behaviour the old Explorer had.
- The legacy InnerNets “engine/steps” experiment has been removed to avoid duplicate logic.
- Logging, artifacts, and metrics match the ai-surfer Explorer output so debugging flows remain familiar.
- Use this doc as the canonical sequence of changes when reviewing history or onboarding another engineer to the migration effort.
