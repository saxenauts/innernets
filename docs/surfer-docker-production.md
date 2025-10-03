# Surfer Docker — Production Checklist

This checklist assumes the Surfer service runs as a companion to InnerNets, providing only the primitive endpoints (search, read-wave, UI agent).

## Runtime settings
- `UVICORN_RELOAD=false`
- `SURFER_ECHO_JOB_LOGS=false`
- `SURFER_LOG_LEVEL=INFO`
- `UVICORN_LOG_LEVEL=warning`
- `UVICORN_ACCESS_LOG=false`
- `HEADFUL=false` (unless you need to observe the browser; enable temporarily for debugging)
- `BROWSER_ENABLED=true`
- `ARTIFACTS_DIR=/app/surfer-agent/.artifacts`

## Health checks
```bash
curl -s http://127.0.0.1:8001/healthz | jq .
```

## API smoke tests
```bash
curl -s http://127.0.0.1:8001/api/google-search \
  -H 'content-type: application/json' \
  -d '{"query":"site:openai.com llm","headless":false}' | jq .

curl -s http://127.0.0.1:8001/api/read-wave \
  -H 'content-type: application/json' \
  -d '{"urls":["https://example.com"],"headless":false}' | jq .

curl -s http://127.0.0.1:8001/api/ui-agent \
  -H 'content-type: application/json' \
  -d '{"provider":"anthropic","model":"claude-sonnet-4-20250514","url":"https://example.com","task":"Open the homepage","headless":false}' | jq .
```

## Observability
- Docker logs capture request-level stdout/stderr when `SURFER_ECHO_JOB_LOGS=true` (default). Disable for quiet mode and persist the `logs` field returned in responses instead.
- Monitor `/healthz` periodically; it resolves the current CDP URL.

## Persistence
- Bind-mount `.artifacts/pw-user` to keep cookies and consent stable.
- Back up provider configuration (`surfer-agent/.env`) securely.

With these settings the Surfer service will remain lightweight, while InnerNets handles the Explorer planning loop in-process.
