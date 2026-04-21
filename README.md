# LLM-Wiki Middleware Delegator

Minimal FastAPI skeleton for ingest, query, and health endpoints for the mem-wiki middleware service.

## Run Locally

```bash
uvicorn server.main:app --reload
```

Server URL: `http://127.0.0.1:8000`

## Smoke Checks

```bash
curl -sS http://127.0.0.1:8000/health
```

```bash
curl -sS "http://127.0.0.1:8000/query?q=hello&limit=3"
```

```bash
curl -sS -X POST http://127.0.0.1:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"source":"smoke-check","payload":"test"}'
```
