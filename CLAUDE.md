# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**mem-weaver** is a FastAPI middleware service that ingests Q/A pairs, processes them through an Ollama LLM pipeline (async), stores results in SQLite with FTS5 full-text search, and generates Markdown wiki pages in an Obsidian-compatible vault.

## Commands

**Setup:**
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # configure as needed
```

**Run server** (requires Ollama running at `http://127.0.0.1:11434`):
```bash
uvicorn server.main:app --reload
```

**Run all tests:**
```bash
./venv/bin/pytest tests/ -v
```

**Run a single test file:**
```bash
./venv/bin/pytest tests/test_textutil.py -v
```

**Run a single test by name:**
```bash
./venv/bin/pytest tests/test_fts_match_terms.py::test_single_word -v
```

**Smoke check** (server must be running):
```bash
./scripts/smoke-check.sh
# Override base URL: BASE_URL=http://127.0.0.1:9000 ./scripts/smoke-check.sh
```

## Architecture

### Request Lifecycle

```
POST /ingest → asyncio.Queue → background worker
                                ├─ Ollama: summarize Q/A → atom + claims + topics
                                ├─ Write raw/qa/<YYYY-MM-DD>/<id>.json  (immutable)
                                ├─ Ollama: generate wiki/<slug>.md
                                ├─ SQLite: upsert pages + qa_pairs + FTS tables
                                ├─ Update wiki/index.md + wiki/log.md
                                ├─ wiki_graph: extract [[wikilinks]], count inbound links
                                └─ contradictions: detect conflicts with stored facts

GET /query?q=<keywords> → SQLite FTS5 BM25 → optional Ollama synthesis → JSON
GET /stats              → aggregate counts, top tags, orphan pages
GET /health             → Ollama liveness, DB status, queue depth
```

### Key Modules

| Path | Role |
|------|------|
| `server/main.py` | FastAPI app, route handlers, lifespan (starts background worker, opens DB) |
| `server/config/settings.py` | Pydantic `BaseSettings`; all tunables via env vars or `.env` |
| `server/pipeline/ingest_worker.py` | Core pipeline: consumes queue, orchestrates all steps |
| `server/pipeline/prompts.py` | All Ollama prompt templates (summarize, wiki page, contradiction check) |
| `server/pipeline/query_search.py` | FTS5 BM25 search; optional Ollama synthesis of results |
| `server/pipeline/contradictions.py` | Conflict detection between incoming and stored facts |
| `server/pipeline/wiki_graph.py` | `[[wikilink]]` extraction and inbound-link counter |
| `server/db/database.py` | `init_db()`, FTS match-term builder |
| `server/db/migrations/001_init.sql` | Full schema: `pages`, `qa_pairs`, `wiki_links`, FTS virtual tables |
| `server/ollama/client.py` | Async Ollama wrapper (`generate_json`, `generate_text`) |

### Data Storage

- **`raw/qa/<date>/<id>.json`** — immutable ingest record, written before any processing
- **`wiki/concepts/<slug>.md`** — Ollama-generated Markdown page (Obsidian wikilinks)
- **`wiki/index.md`** / **`wiki/log.md`** — auto-updated table of contents and ingest log
- **`db/wiki.db`** — SQLite: `pages`, `qa_pairs`, `wiki_links`, `pages_fts`, `qa_fts`
- **`dlq/`** — dead-letter queue: JSON files for ingests that failed the pipeline

### Ingest ID format

`ing_<YYYYMMDD>_<8-hex-chars>` — e.g., `ing_20260422_a1b2c3d4`

## Configuration (`.env` / env vars)

Key settings from `server/config/settings.py`:

| Variable | Default | Purpose |
|----------|---------|---------|
| `OLLAMA_HOST` | `http://127.0.0.1:11434` | Ollama endpoint |
| `OLLAMA_MODEL` | `llama3.2` | Model used for all LLM calls |
| `WIKI_DIR` | `wiki` | Root of the Markdown vault |
| `RAW_DIR` | `raw` | Root of immutable Q/A JSON store |
| `DB_PATH` | `db/wiki.db` | SQLite database path |
| `DLQ_DIR` | `dlq` | Dead-letter queue directory |
| `MAX_QUEUE_SIZE` | `100` | Ingest queue cap |

## Testing

Tests live in `tests/`. `pytest.ini` sets `asyncio_mode = auto` and `pythonpath = .`.

- Unit tests mock Ollama via `unittest.mock` — no live Ollama required.
- Integration test (`test_ingest_integration.py`) exercises the full ingest → query roundtrip with mocked Ollama responses.
- Smoke check (`scripts/smoke-check.sh`) requires both server and Ollama to be running.

## Conventions

- **Commits:** Conventional Commits — `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`
- **Async:** all I/O is async (`aiosqlite`, `httpx`); the ingest queue runs as a `asyncio.Task` in the FastAPI lifespan.
- **Pydantic v2** for all request/response models (`server/models/api.py`).
