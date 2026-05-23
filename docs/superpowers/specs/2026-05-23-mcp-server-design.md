# MCP Server — Design Doc

**Date:** 2026-05-23  
**Status:** Approved  
**Stack:** FastMCP · Python 3.12 · stdio MCP · FastAPI (shared service layer) · SQLite FTS5 + sqlite-vec · Ollama

---

## 1. Overview

Expose mem-weaver as a **standalone stdio MCP server** so IDEs (Cursor, Claude Code, Opencode) can search and write project wiki memory mid-coding session — without running the FastAPI server or chat frontend.

The existing `/query`, `/ingest`, and `/wiki/{slug}` endpoints map cleanly to MCP tools. `/chat` is intentionally **not** exposed: the IDE agent is already the LLM; it searches memory, answers itself, and persists learnings via ingest.

### Key decisions (brainstorming outcomes)

| Decision | Choice |
|----------|--------|
| Transport | **Standalone stdio** — IDE spawns `python -m server.mcp_server` |
| Implementation | **FastMCP** + shared **`memory_api` service layer** (Approach 2) |
| Tool surface | `wiki_search`, `wiki_ingest`, `wiki_get_page`, `wiki_stats` |
| Runtime model | **MCP-only in IDE** — self-contained DB init + ingest worker; do not run uvicorn concurrently |
| Chat / SSE | Out of scope — no `wiki_chat` tool in v1 |

### Success criteria

1. Cursor MCP panel shows 4 mem-weaver tools after config + restart.
2. Agent can `wiki_search` and receive hybrid-ranked snippets from the local wiki.
3. Agent can `wiki_ingest` a Q/A; page appears in `wiki/concepts/` after background Ollama compile (~30–60s).
4. `wiki_stats` reports page counts and Ollama reachability.
5. HTTP routes in `main.py` delegate to the same service functions — no duplicated business logic.

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  IDE (Cursor / Claude Code / Opencode)                      │
│  spawns: python -m server.mcp_server                        │
└──────────────────────────┬──────────────────────────────────┘
                           │ stdio (MCP protocol)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  server/mcp_server.py          (FastMCP, stdio transport)   │
│  ├─ lifespan: init_db + ingest worker task                  │
│  └─ 4 tool handlers → server/services/memory_api.py         │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  server/services/memory_api.py   (shared service layer)     │
│  search_wiki() │ enqueue_ingest() │ get_wiki_page() │ stats │
└──────────┬───────────────────────────────┬──────────────────┘
           │                               │
           ▼                               ▼
┌──────────────────────┐      ┌───────────────────────────────┐
│  Pipeline modules     │      │  server/main.py               │
│  query_search,        │◄─────│  thin routes → memory_api     │
│  ingest_worker,       │      └───────────────────────────────┘
│  embedder, database   │
└──────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│  SQLite (db/wiki.db) + wiki/ markdown vault + Ollama          │
└─────────────────────────────────────────────────────────────┘
```

### Properties

- **Two entry points, one brain.** `main.py` and `mcp_server.py` are thin adapters; `memory_api.py` owns shared logic.
- **No HTTP hop.** MCP imports pipeline modules directly.
- **Mutual exclusion by convention.** Document: do not run uvicorn and MCP ingest simultaneously (two workers, same DB/wiki files).

### Files

| File | Action |
|------|--------|
| `server/services/memory_api.py` | **New** — 4 shared async functions |
| `server/mcp_server.py` | **New** — FastMCP server + lifespan |
| `server/main.py` | **Modify** — routes delegate to `memory_api` |
| `requirements.txt` | **Add** `fastmcp` |
| `tests/test_memory_api.py` | **New** — unit tests |
| `tests/test_mcp_server.py` | **New** — in-process MCP smoke test |
| `README.md` | **Modify** — MCP setup section |
| `.cursor/mcp.json.example` | **New** — example IDE config (not user-specific paths) |

---

## 3. MCP Tools

Server metadata:

```python
mcp = FastMCP(
    "mem-weaver",
    instructions=(
        "Local wiki memory for this project. "
        "Use wiki_search before answering questions about project knowledge. "
        "Use wiki_ingest to persist useful Q/A after solving problems."
    ),
)
```

### 3.1 `wiki_search`

Hybrid FTS5 + vector search (default). Same semantics as `GET /query`.

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `query` | `str` | required | Natural-language search |
| `limit` | `int` | `5` | Clamped 1–20 (HTTP allows 50; lower cap saves IDE tokens) |
| `mode` | `"hybrid" \| "keyword" \| "semantic"` | `"hybrid"` | |

**Returns:**

```json
{
  "query": "how does RRF work",
  "mode": "hybrid",
  "total": 3,
  "results": [
    {
      "title": "Hybrid Search",
      "path": "concepts/hybrid-search",
      "snippet": "...reciprocal rank fusion...",
      "score": 0.82,
      "tags": ["search"]
    }
  ]
}
```

No `summarize` param in v1 — IDE agent synthesizes from snippets.

### 3.2 `wiki_ingest`

Async Q/A compile pipeline (same as `POST /ingest`).

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `question` | `str` | required | |
| `answer` | `str` | required | |
| `tags` | `list[str]` | `[]` | |
| `source` | `str` | `"mcp"` | Identifies IDE-origin ingests |

**Returns:**

```json
{
  "status": "accepted",
  "ingest_id": "ing_20260523_a1b2c3d4",
  "message": "Queued for wiki compilation. Page will appear after Ollama processing (~30-60s)."
}
```

### 3.3 `wiki_get_page`

Full markdown by slug (same as `GET /wiki/{slug}`).

| Param | Type | Default |
|-------|------|---------|
| `slug` | `str` | required — e.g. `concepts/hybrid-search` (no `.md`) |

**Returns:** `{ "slug": "...", "content": "..." }`. Empty `content` if not found (not an error).

### 3.4 `wiki_stats`

Vault health snapshot — merges `/stats` counters with lightweight Ollama ping and queue depth.

**Returns:**

```json
{
  "wiki_pages": 42,
  "qa_pairs": 38,
  "orphan_pages": 3,
  "top_tags": [["python", 12], ["fastapi", 8]],
  "last_ingest": "2026-05-22T14:30:00+00:00",
  "ollama": "reachable",
  "queue_depth": 0
}
```

### Out of scope (v1)

- MCP resources (browsable wiki URIs)
- `wiki_chat` / SSE streaming
- Auth / multi-tenant scoping
- Concurrent FastAPI + MCP ingest

---

## 4. Service Layer

### `server/services/memory_api.py`

```python
async def search_wiki(
    settings: Settings,
    query: str,
    *,
    limit: int = 5,
    mode: QueryMode = QueryMode.HYBRID,
) -> dict[str, Any]: ...

async def enqueue_ingest(
    settings: Settings,
    queue: asyncio.Queue[IngestJob],
    *,
    question: str,
    answer: str,
    source: str = "mcp",
    tags: list[str] | None = None,
    session_id: str | None = None,
) -> dict[str, str]: ...

async def get_wiki_page(settings: Settings, slug: str) -> dict[str, str]: ...

async def get_wiki_stats(
    settings: Settings,
    queue: asyncio.Queue[IngestJob] | None = None,
) -> dict[str, Any]: ...
```

### `main.py` refactor

| Route | Change |
|-------|--------|
| `GET /query` | Delegate to `search_wiki()` → wrap in `QueryResponse` |
| `POST /ingest` | Delegate to `enqueue_ingest()` → wrap in `IngestResponse` |
| `GET /wiki/{slug}` | Delegate to `get_wiki_page()` → wrap in `WikiResponse` |
| `GET /stats` | Delegate to `get_wiki_stats()` → wrap in `StatsResponse` |
| `GET /health` | **Unchanged** — HTTP-only ops endpoint |

`summarize=True` on `/query` stays in the route handler (calls `synthesize_answer` after `search_wiki`) — not exposed via MCP.

---

## 5. MCP Lifecycle

On `server/mcp_server` startup:

```
1. settings = get_settings()
2. await init_db(settings)
3. queue = asyncio.Queue(maxsize=settings.max_queue_size)
4. worker = asyncio.create_task(ingest_worker_loop(queue, settings))
5. Register tools (closure over settings + queue)
6. mcp.run()  → stdio transport, blocks until IDE disconnects
7. On shutdown: cancel worker task
```

**Entry point:** `python -m server.mcp_server`  
**Working directory:** repo root (relative `wiki/`, `db/` paths).

`McpContext` dataclass holds `(settings, queue, worker_task)` for tool handlers.

---

## 6. Error Handling

MCP tools return structured JSON error dicts as tool result text — not uncaught exceptions.

| Scenario | Behavior |
|----------|----------|
| Empty query / missing required param | `{"error": "query must not be empty"}` |
| Ingest queue full | `{"error": "ingest queue full", "queue_depth": N}` |
| Search failure (all channels) | `{"error": "search failed", "detail": "..."}` |
| Hybrid search, Ollama down for embeddings | FTS keyword results still returned when possible |
| Ingest accepted, Ollama down at compile time | Async DLQ — same as HTTP path |
| Wiki slug not found | `{"slug": "...", "content": ""}` |
| DB unavailable | `{"error": "database unavailable"}` |

Logging: `INFO` on tool invocation (name + param summary); `ERROR` + stack trace on unexpected failures. Namespace: `server.services.memory_api`.

No additional retry layer in MCP — Ollama client retains existing 3-retry backoff.

---

## 7. IDE Configuration

Example `.cursor/mcp.json.example` (committed; users copy and adjust paths):

```json
{
  "mcpServers": {
    "mem-weaver": {
      "command": "./venv/bin/python",
      "args": ["-m", "server.mcp_server"],
      "cwd": "/absolute/path/to/mem-weaver",
      "env": {
        "OLLAMA_MODEL": "qwen3.5:latest"
      }
    }
  }
}
```

**Prerequisites (README MCP section):**

1. Ollama running (`ollama serve`)
2. Model pulled
3. Venv created; `pip install -r requirements.txt`
4. Do **not** run `uvicorn` while using MCP ingest

---

## 8. Testing

### Unit — `tests/test_memory_api.py`

Temp DB/wiki dir; mock Ollama (same fixtures as `test_ingest_integration.py`):

| Test | Verifies |
|------|----------|
| `test_search_wiki_hybrid` | Ranked results from seeded pages |
| `test_search_wiki_empty_query` | Validation error dict |
| `test_enqueue_ingest_accepted` | Returns `ingest_id`; job in queue |
| `test_enqueue_ingest_queue_full` | Queue-full error when `maxsize=0` |
| `test_get_wiki_page_found` | Reads markdown from temp wiki |
| `test_get_wiki_page_missing` | Empty content, no exception |
| `test_get_wiki_stats` | Counts match seeded data |

### MCP smoke — `tests/test_mcp_server.py`

FastMCP in-process `Client` (no subprocess):

- `list_tools()` includes all 4 tool names
- `call_tool("wiki_stats", {})` returns parseable JSON with `wiki_pages`

### Manual checklist

1. Copy MCP config → Cursor restart → 4 tools visible
2. Prompt: "search my wiki for FastAPI" → `wiki_search` invoked
3. Prompt: save a learning → `wiki_ingest` → page in `wiki/concepts/` after ~60s
4. `wiki_stats` shows incremented counts

### Not tested in v1

- Concurrent FastAPI + MCP
- Remote / HTTP MCP transport
- Chat / SSE

---

## 9. Dependencies

Add to `requirements.txt`:

```
fastmcp>=2.0,<4
```

(Pin upper bound at implementation time to match repo convention.)

---

## 10. Future (post-v1)

- MCP resources: `wiki://concepts/{slug}` for direct page reads
- `wiki_retrieve_context` — Phase A context without LLM (classify + retrieve)
- File-lock or single-worker coordination for concurrent FastAPI + MCP
- `fastmcp run` dev mode with live reload
