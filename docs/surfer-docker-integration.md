# Surfer Docker Integration (InnerNets)

Use this guide to run the Surfer service locally and wire it into InnerNets. The service now exposes only the low-level primitives; the Explorer loop lives in-process inside InnerNets.

## Run the service

```bash
docker compose up --build
```

- API: `http://127.0.0.1:8001`
- Browser (CDP): `ws://127.0.0.1:9222/devtools/browser/...`
- noVNC viewer: `http://localhost:6080`
- Artifacts: `./.artifacts` bind-mounted into the container

Health check:
```bash
curl -s http://127.0.0.1:8001/healthz | jq .
```

## API calls from InnerNets

InnerNets uses two endpoints:
- `POST /api/google-search`
- `POST /api/read-wave`

You can exercise them manually:
```bash
curl -s http://127.0.0.1:8001/api/google-search \
  -H 'content-type: application/json' \
  -d '{"query":"latest llm release","headless":true}' | jq .

curl -s http://127.0.0.1:8001/api/read-wave \
  -H 'content-type: application/json' \
  -d '{"urls":["https://news.ycombinator.com"],"headless":true}' | jq .
```

Each response returns `{ result, logs }`. InnerNets stores both to keep run traces.

## Environment tips
- Keep `SURFER_BASE_URL=http://host.docker.internal:8001` in InnerNets env files.
- Set `SURFER_HEADLESS=0` locally if you want to watch the browser via noVNC.
- Provide provider keys (Anthropic, OpenAI, Azure, etc.) through `surfer-agent/.env`.

## Production notes
- Disable dev reload: `UVICORN_RELOAD=false`.
- Quiet logs: set `SURFER_ECHO_JOB_LOGS=false`, `UVICORN_ACCESS_LOG=false`.
- Persist `.artifacts/pw-user` between deployments to preserve cookies.

That's all — start the service, point InnerNets at it, and the in-process Explorer will call the primitives during each run.
