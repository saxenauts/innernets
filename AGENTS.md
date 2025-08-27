# Repository Guidelines

## Project Structure & Monorepo Layout
- This is a monorepo. Use top-level `frontend/` and `backend/` folders. Each area maintains its own `AGENTS.md`. Avoid deep nesting.
- Current folders: `docs/` (planning, e.g., `Phase-1.md`), `README.md`.
- When code is added, colocate tests with each service (e.g., `frontend/src/test/`, `backend/tests/`).

## Build, Test, and Development
- No build required yet (Markdown only). View docs in `docs/` locally or on GitHub.
- Optional Markdown hygiene:
  - `npx markdownlint docs/**/*.md` — style checks.
  - `npx prettier --check docs/**/*.md` — formatting.

## Professional Standards (Frontend & Backend)
- Frontend: accessible (WCAG-aware), responsive, consistent design tokens, performance budgets, semantic HTML, typed code where applicable.
- Backend: clear API contracts, input validation, structured logging, idempotent handlers, least-privilege access, predictable error models, and Pydantic models at service boundaries (no plain dicts).
- Shared: avoid secrets in repo, follow OWASP basics, document configuration and operational runbooks.

## Testing & TDD
- Prefer test-driven development wherever feasible: write/adjust tests before implementation.
- Frontend: component/integration tests for UI states; backend: unit tests for domain logic and API contracts.
- Name tests `test_<feature>.*`; keep them fast and deterministic. Example layout: `frontend/src/test/`, `backend/tests/`.

## Commit & Pull Requests
- Use clear, imperative messages (Conventional Commits encouraged: `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`).
- Keep PRs focused; include summary, motivation, linked issues, and screenshots or logs when helpful. Update relevant `AGENTS.md` and docs.

## Index, Logs & Maintenance
- Maintain a basic index here of service docs (update as services are added):
  - `frontend/AGENTS.md` — Web frontend guidelines
  - Example: `backend/AGENTS.md`.
- Use `docs/updates.md` for:
  - Updates Log: brief, dated natural-language updates with references.
  - Task Board: Todo / In Progress / Done checklists to track work.
- After each successful change or when adding new tasks, update:
  - The service’s local `AGENTS.md` with specifics for that area, and
  - `docs/updates.md` (both the update entry and task movement).
