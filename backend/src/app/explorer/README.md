Explorer Engine (InnerNets Port)

Scope
- Direct port of the ai-surfer Explorer “planning brain” into InnerNets.
- Houses prompts, models, logging, and orchestration code so the workflow can run in-process.

Structure
- `runner.py` — Owns the full Explorer loop (planner → SERP filter → reading waves → curation).
- `prompts.py` — Prompt templates shared across planner/filter/reader models.
- `models.py` — Pydantic schemas for LLM I/O, memory state, and outputs.
- `llm.py` — Helpers to call Azure OpenAI with schema enforcement.
- `logger.py` / `ansi.py` — Structured logging mirroring the ai-surfer console output.

Operational Notes
- The module expects `app.clients.surfer_client.google_search` and `read_wave` to be available; these talk to the ai-surfer service for SERP capture and markdown rendering.
- Artifacts are written under `.artifacts/innernets-explorer/` (see `surfer_workflow.py`).
- See `docs/ai-surfer-migration.md` for the full migration log and follow-up items.
