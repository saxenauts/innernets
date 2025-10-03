# Surfer Docker Service — API Summary

Base URL (compose default): `http://host.docker.internal:8001`

## Envelope
- Most endpoints return `{ result, logs }`.
- `/api/read-markdown` returns `{ content, references }` without logs.

## Endpoints
- `POST /api/google-search`
  - Body: `{ query, cdp_url?, headless? }`
  - Result: normalized SERP items inside `result.items.serp.items[]`.
- `POST /api/read-wave`
  - Body: `{ urls: string[], cdp_url?, headless?, citations?, prune? }`
  - Result: `{ pages: [{ url, content, references?, links[] }] }`.
- `POST /api/read-markdown`
  - Same options as `read-wave`, but for a single URL.
- `POST /api/markdown/crawl4ai`
  - Experimental access to Crawl4AI options (selectors, JS, waits, etc.).
- `POST /api/ui-agent`
  - Body: `{ provider, model?, url, task, cdp_url?, headless?, leave_open?, temperature?, grounding?, moondream_base? }`
  - Result includes the echo of provider/model/url/task and the captured run logs.
- `GET /healthz` → `{ status, services, cdp_url, version }`
- `GET /version` → `{ package?, fastapi?, python }`
- Debug endpoints: `/debug/tabs`, `/debug/screenshot`, `/cdp/json/list`, `/debug/navigate`.

## Examples
```bash
# Read two pages
curl -s http://host.docker.internal:8001/api/read-wave \
  -H 'content-type: application/json' \
  -d '{"urls":["https://news.ycombinator.com","https://example.com"],"headless":true}' | jq .

# Google search
curl -s http://host.docker.internal:8001/api/google-search \
  -H 'content-type: application/json' \
  -d '{"query":"agentic browsing","headless":false}' | jq .

# UI agent (Anthropic)
curl -s http://host.docker.internal:8001/api/ui-agent \
  -H 'content-type: application/json' \
  -d '{"provider":"anthropic","model":"claude-sonnet-4-20250514","url":"https://example.com","task":"Open the homepage","headless":false}' | jq .
```

All responses include `logs`, so persist the JSON body to capture both the structured result and the trace for auditing.
