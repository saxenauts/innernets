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

## Service Wrapper (SDK-first)

Workers call our thin wrapper around `exa-py` (no public HTTP routes):

- `ExaClient.search_and_contents(query, type, num_results, text|highlights|summary, ...)`
- `ExaClient.get_contents(urls, text|highlights|summary, ...)`

Contract & caps
- Use the Python SDK signature (snake_case) and pass only documented fields.
- Enforce caps per `docs/search-only-plan.md`:
  - `num_results ≤ 25` for `neural/auto`
  - `num_results ≤ 100` for `keyword`

## SDK Reference

Under the hood we use `exa-py` from `app/clients/exa_client.py`:

- `search_and_contents(query, type="auto", num_results=10, contents={...}, **kwargs)`
- `get_contents(urls=[...], text=True, **kwargs)`

These map to Exa’s `/search` and `/contents` endpoints respectively. We pass through most documented fields.

Contract choice
- We use the Python SDK as the reference. Public API uses snake_case and top-level fields to match SDK signatures exactly.
- Responses are normalized to plain dicts and validated into Pydantic models, so downstream always receives typed data.

## Cost & Guardrails

- Exa includes `costDollars` in responses; our API forwards it as `provider_cost`.
- Defaults encourage low cost per docs/search-only-plan.md.

### Pricing (simple)
- Search requests (≤100 results):
  - keyword: about $0.0025 per request
  - neural/auto (≤25 results): about $0.0050 per request
  - neural/auto (26–100 results): pricier tier (avoid by keeping `num_results ≤ 25`).
- Contents per page (each option adds cost):
  - text: ~$0.001 per page
  - highlights: ~$0.001 per page
  - summary: ~$0.001 per page
- Example: 10 keyword results + read text for 5 pages ≈ $0.0025 + (5 × $0.001) = $0.0075
- We meter exact cost via `provider_cost.total` in responses.

## Auth

- No user JWT is required for Exa; calls are executed with `EXA_API_KEY` set in server environment.
- Worker attribution: costs are recorded under the job’s `user_id` in run metrics.

## Example (Python)

from app.clients.exa_client import get_exa_client

exa = get_exa_client()
res = exa.search_and_contents(
    query="latest banana model from google",
    type="keyword",
    num_results=3,
    text={"max_characters": 1500},
)
first = (res.get("results") or [])[0]
print(first.get("title"), first.get("url"))

res2 = exa.get_contents(urls=[first["url"]], text={"max_characters": 1500})
print(len(res2.get("results") or []), "pages")

---

Appendix: Exa Python SDK Reference (subset)

The following is a condensed version of the Exa Python SDK spec for quick reference. See the official docs for full details.

- `exa.search(query, num_results=10, include_domains=None, exclude_domains=None, start_crawl_date=None, end_crawl_date=None, start_published_date=None, end_published_date=None, type="auto", category=None, context=None)` → SearchResponse[Result]

- `exa.search_and_contents(query, text: Union[bool, TextOptions]=None, highlights: Union[bool, HighlightsOptions]=None, num_results=10, include_domains=None, exclude_domains=None, start_crawl_date=None, end_crawl_date=None, start_published_date=None, end_published_date=None, type="auto", category=None, context=None)` → SearchResponse[ResultWithText/Highlights/Both]

- `exa.get_contents(urls: List[str], text: Union[bool, TextOptions]=None, highlights: Union[bool, HighlightsOptions]=None, summary: Optional[Dict]=None, livecrawl: Optional[str]=None, livecrawl_timeout: Optional[int]=None, subpages: Optional[int]=0, subpage_target: Optional[Union[str, List[str]]]=None, extras: Optional[Dict]=None, context: Optional[Union[bool, Dict[str, int]]]=None)` → ContentsResponse

Pricing-friendly defaults we use:
- Default `num_results=25` for `neural/auto` to stay in lower tier; enforce `≤ 25`.
- Allow `keyword` up to `100`, but keep payloads modest to control cost.
- Prefer `text` only for reads; avoid highlights/summary unless specifically needed.

## Troubleshooting

- `401 Unauthorized`: ensure you pass a valid Supabase access token; the backend verifies with `SUPABASE_JWT_SECRET`.
- `502 Exa error`: backend could not reach Exa or SDK raised. Check `EXA_API_KEY` and network access.
- Validation errors on `numResults`: adjust per caps above.
