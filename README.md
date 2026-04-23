# LLM-Wiki Middleware Delegator

FastAPI service that implements the **s2 ingest pipeline** ([`docs/s2-claude-plan.md`](docs/s2-claude-plan.md)): `POST /ingest` returns **202** immediately, then **Ollama** distills Q/A, writes **immutable raw JSON**, updates **markdown** under `wiki/`, and indexes **SQLite FTS5** for `GET /query`. Designed for **localhost**; no API-key auth in this phase.

## Dependencies

Use Python 3.12 or newer. Install packages into a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Run Locally

```bash
uvicorn server.main:app --reload
```

Server URL: `http://127.0.0.1:8000`

## Settings

Runtime settings use **pydantic-settings** (env vars and optional `.env`). See [`.env.example`](.env.example).

| Variable | Default | Purpose |
|----------|---------|---------|
| `APP_NAME` | `LLM-Wiki Middleware Delegator` | FastAPI title |
| `APP_ENV` | `development` | Environment label |
| `HOST` | `127.0.0.1` | Bind address |
| `PORT` | `8000` | Bind port |
| `OLLAMA_HOST` | `http://127.0.0.1:11434` | Ollama base URL |
| `OLLAMA_MODEL` | `minimax-m2.7:cloud` | Model for summarize + wiki body |
| `OLLAMA_TIMEOUT` | `120` | HTTP timeout (seconds) |
| `WIKI_DIR` | `wiki` | Markdown vault root |
| `RAW_DIR` | `raw/qa` | Immutable Q/A JSON root |
| `DB_PATH` | `db/wiki.db` | SQLite database |
| `MAX_QUEUE_SIZE` | `100` | Ingest queue depth before `503` |

Example:

```bash
OLLAMA_MODEL=minimax-m2.7:cloud uvicorn server.main:app --reload
```

**Prerequisite:** Ollama running locally (`ollama serve`) with the configured model available.

## Smoke Checks

With **uvicorn** already running on the default host/port:

```bash
./scripts/smoke-check.sh
```

This calls `GET /health`, `GET /stats`, `GET /query`, `POST /ingest` (expects **202**), then `GET /query?q=smoke` (hits may still be empty until the async worker finishes). Override the base URL with `BASE_URL` if needed.

After ingest, you can poll `GET /stats` or `GET /query?q=…` until new data appears (pipeline is async).
