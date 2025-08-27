# Exa Integration Usage

This backend integrates Exa (search engine for AIs) via the official Python SDK `exa-py`.

## Install & Run

- Ensure dependencies are installed:
  - `cd backend && poetry install`
- Set environment variables (create `backend/.env` from `.env.example`):
  - `EXA_API_KEY=...` (from https://dashboard.exa.ai)
  - Optional: `EXA_BASE_URL=https://api.exa.ai`
- Start the API:
  - `poetry run uvicorn app.main:app --reload`

## Endpoints

- POST `/exa/search`
  - Mirrors Exa `/search` with optional `contents` block to fetch text alongside results.
  - Body (minimal): `{ "query": "Latest research in LLMs", "type": "keyword", "numResults": 10, "contents": { "text": true } }`
  - Returns (typed):
    - `requestId: string`
    - `resolvedSearchType: string`
    - `results: ResultWithContent[]`
    - `searchType: string`
    - `context?: string`
    - `provider_cost: CostDollars` (mirrors Exa `costDollars` schema)
  - Caps: `numResults ≤ 25` for `neural/auto`; `≤ 100` for `keyword`.

- POST `/exa/contents`
  - Mirrors Exa `/contents` for a list of URLs.
  - Body (minimal): `{ "urls": ["https://example.com"], "text": true }`
  - Returns (typed):
    - `requestId: string`
    - `results: ResultWithContent[]`
    - `statuses?: { id: string, status: 'success'|'error', error?: { tag: string, httpStatusCode?: number } }[]`
    - `context?: string`
    - `provider_cost: CostDollars`

## SDK Reference

Under the hood we use `exa-py` from `app/clients/exa_client.py`:

- `search_and_contents(query, type="auto", num_results=10, contents={...}, **kwargs)`
- `get_contents(urls=[...], text=True, **kwargs)`

These map to Exa’s `/search` and `/contents` endpoints respectively. We pass through most documented fields.

Contract fidelity
- Public API follows Exa docs (camelCase JSON, nested `contents`).
- Internally we use the Python SDK (snake_case). A small adapter converts request fields once and normalizes SDK responses.
- Routes validate into Pydantic models so downstream always receives typed data.

## Cost & Guardrails

- Exa includes `costDollars` in responses; our API forwards it as `provider_cost`.
- Defaults encourage low cost per docs/search-only-plan.md:
  - Prefer `keyword` for most queries; use `neural` selectively.
  - Avoid `highlights` and `summary` unless needed (each adds ~$0.001/page).
  - Optionally cap `text.maxCharacters` to control payload size.

## Auth

- All `/exa/*` routes require Supabase JWT (`Authorization: Bearer <access_token>`). For local testing in pytest, we override the dependency.

## Examples

curl — Search + Text Contents

curl --request POST \
  --url http://localhost:8000/exa/search \
  --header 'Authorization: Bearer <SUPABASE_ACCESS_TOKEN>' \
  --header 'Content-Type: application/json' \
  --data '{
    "query": "Latest research in LLMs",
    "type": "keyword",
    "numResults": 10,
    "contents": { "text": true }
  }'

curl — Contents Only

curl --request POST \
  --url http://localhost:8000/exa/contents \
  --header 'Authorization: Bearer <SUPABASE_ACCESS_TOKEN>' \
  --header 'Content-Type: application/json' \
  --data '{
    "urls": ["https://arxiv.org/abs/2307.06435"],
    "text": true
  }'

## Troubleshooting

- `401 Unauthorized`: ensure you pass a valid Supabase access token; the backend verifies with `SUPABASE_JWT_SECRET`.
- `502 Exa error`: backend could not reach Exa or SDK raised. Check `EXA_API_KEY` and network access.
- Validation errors on `numResults`: adjust per caps above.
