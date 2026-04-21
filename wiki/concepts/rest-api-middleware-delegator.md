---
id: rest-api-middleware-delegator
title: "REST API — middleware delegator"
type: concept
tags: [api, fastapi, ingest, query]
confidence: high
created: 2026-04-21
updated: 2026-04-21
---

# REST API — middleware delegator

HTTP surface between any LLM client and the LLM-wiki memory store. Full target contract: `docs/s2-claude-plan.md` §3. Implementation entrypoint: `server/main.py`; models: `server/models/api.py`.

## Base URL

Default local: `http://127.0.0.1:8000` (`uvicorn server.main:app --reload`).

## Endpoints

### `GET /health`

Liveness plus `ollama`, `db`, `queue_depth`, `wiki_pages`, `qa_pairs` (see `docs/s2-claude-plan.md` §3.3).

```bash
curl -sS http://127.0.0.1:8000/health
```

### `GET /query`

Retrieval over compiled wiki pages (FTS5 BM25). **`summarize=true`** runs Ollama over top snippets (extra latency/tokens).

```bash
curl -sS "http://127.0.0.1:8000/query?q=attention&limit=5"
curl -sS "http://127.0.0.1:8000/query?q=attention&limit=3&summarize=true"
```

`q` is required (422 if missing).

### `POST /ingest`

Structured Q/A handoff. **Implemented:** required `question` and `answer`; optional `source`, `session_id`, `tags`, `timestamp`. Returns `202` immediately; worker runs Ollama (default model `minimax-m2.7:cloud`), writes `raw/qa/YYYY-MM-DD/<ingest_id>.json`, updates `wiki/concepts/<slug>.md`, SQLite `pages` / `qa_pairs`, and FTS rows.

```bash
curl -sS -X POST http://127.0.0.1:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"question":"What is X?","answer":"X is ..."}'
```

### `GET /stats`

Aggregate counters (`total_ingests`, `total_wiki_pages`, `last_ingest`, …). See `docs/s2-claude-plan.md` §3.4.

```bash
curl -sS http://127.0.0.1:8000/stats
```

## Mapping to Karpathy operations

| Gist operation | Endpoint |
|----------------|----------|
| Ingest | `POST /ingest` |
| Query | `GET /query` |
| Lint | manual / future route |

Agent rules for maintaining this page: `wiki/LLM_WIKI_SCHEMA.md`.
