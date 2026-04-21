# LLM-Wiki Middleware Delegator

Minimal FastAPI skeleton for ingest, query, and health endpoints for the mem-wiki middleware service.

## Run Locally

```bash
uvicorn server.main:app --reload
```

Server URL: `http://127.0.0.1:8000`

## Settings

Runtime settings are loaded from environment variables (and optional `.env`):

- `APP_NAME` (default: `LLM-Wiki Middleware Delegator`)
- `APP_ENV` (default: `development`)
- `HOST` (default: `127.0.0.1`)
- `PORT` (default: `8000`)

Example:

```bash
APP_ENV=development uvicorn server.main:app --reload
```

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
