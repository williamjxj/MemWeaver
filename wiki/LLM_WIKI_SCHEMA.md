# Agent schema — REST delegator and LLM-Wiki

This file is the **schema layer** (Karpathy’s “third layer”): conventions for how an agent should treat this repository’s wiki, raw store, and HTTP API together. Primary idea reference: [Karpathy — LLM Wiki (gist)](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f). Product plan for this service: `docs/s2-claude-plan.md`. NotebookLM-style value gate and async handoff: `docs/s2-notebooklm.md`.

## Three layers (mapped to this repo)

| Layer | Role here | Location |
|--------|-----------|----------|
| **Raw** | Immutable inputs (Q/A JSON once pipeline persists them) | `raw/qa/YYYY-MM-DD/` (see s2 plan) |
| **Wiki** | Persistent, interlinked markdown the system and humans read | `wiki/` (this tree) |
| **Schema** | Rules for ingest, query, lint, logging | **This file** + `docs/s2-claude-plan.md` |

## Operations over HTTP (delegator)

| LLM-Wiki operation (gist) | REST surface | Notes |
|---------------------------|--------------|--------|
| **Ingest** (add knowledge) | `POST /ingest` | **Implemented:** JSON `question` + `answer` (required), optional `source`, `session_id`, `tags`, `timestamp`; `202` + `ingest_id`; background Ollama → `raw/qa/…` → `wiki/concepts/…` → SQLite + `pages_fts`. |
| **Query** (retrieve compiled knowledge) | `GET /query?q=…&limit=…&mode=hybrid&summarize=…` | **Implemented:** Three modes — `keyword` (FTS5 BM25), `semantic` (vector cosine similarity via sqlite-vec), `hybrid` (RRF merge). Optional `summarize=true` runs Ollama over top snippets. |
| **Lint** (health of wiki) | Not a dedicated route yet | Run from agent: scan `wiki/` for orphans, stale links, contradictions; append findings to `wiki/log.md`. Optional future: `POST /lint` or MCP tool. |
| **Liveness** | `GET /health` | Process up; future fields: `ollama`, `db`, queue depth (s2). |

## Semantic search (embeddings)

The system now supports hybrid search — FTS5 BM25 + vector cosine similarity merged via Reciprocal Rank Fusion:

- **Embedding model:** `nomic-embed-text` (768-d) via Ollama `/api/embeddings`
- **Vector storage:** `page_embeddings` vec0 table in SQLite (via `sqlite-vec` extension)
- **Embedding trigger:** Automatic in the ingest pipeline (async, ~200ms overhead, non-blocking)
- **Query modes:**
  - `keyword` — pure FTS5 BM25 (deterministic, zero Ollama overhead)
  - `semantic` — pure vector cosine similarity (semantic matching)
  - `hybrid` — both merged via RRF with k=60 (default)

Hybrid mode (`GET /query?q=attention&mode=hybrid`) runs FTS5 and vector search in parallel, then merges ranks. It catches semantic matches that keyword-only search misses — e.g., searching "memory" also surfaces pages about "recall."

Always prefer **deterministic retrieval** (this wiki’s `index.md`, SQLite FTS) before burning context on full-graph reasoning, per `docs/s2-notebooklm.md` and thread consensus in the gist comments.

## Mandatory wiki maintenance

1. After any **meaningful** API or pipeline change: update `wiki/concepts/rest-api-middleware-delegator.md` and one-line entries in `wiki/index.md`.
2. After each ingest session (when raw JSON exists): append a line to `wiki/log.md` using prefix `## [YYYY-MM-DD] ingest | <short title>`.
3. Prefer **wikilinks** between concept pages: `[[rest-api-middleware-delegator]]`.

## REST usage for agents

Base URL default: `http://127.0.0.1:8000` (override via deploy env).

```http
GET /health
GET /query?q=<keywords>&limit=<n>
POST /ingest
Content-Type: application/json

{ "question": "...", "answer": "..." }
```

Trust `server/models/api.py` for the exact Pydantic contract; this wiki tracks **intent**, Karpathy alignment, and operational notes beyond OpenAPI.

## Contradiction and trust

- **Source of truth for facts** remains immutable **raw** JSON once written; wiki pages are **compiled views** (s2 + Karpathy).
- When raw and wiki disagree, **raw wins**; fix wiki via a new ingest or an explicit edit logged in `wiki/log.md`.
