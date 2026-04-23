# LLM-Wiki Middleware Delegator — Implementation Plan

**Version:** 1.0  
**Date:** 2026-04-21  
**Stack:** Python 3.12 · FastAPI · Ollama (glm-4.7-flash) · SQLite FTS5 · Markdown

---

## 1. Overview

The **Middleware Delegator** is a stateless HTTP daemon that sits between any LLM chat client and the llm-wiki knowledge store. It has one job: accept raw Q/A pairs, compress them into clean knowledge atoms via Ollama, persist them as both structured records (SQLite) and human-readable wiki pages (Markdown), and serve keyword queries back against that growing index.

```
┌─────────────────────┐        POST /ingest         ┌──────────────────────────────────┐
│   Any LLM Client    │ ──────────────────────────► │                                  │
│  (Claude, Cursor,   │                             │   Middleware Delegator           │
│   OpenCode, etc.)   │        GET /query?q=...     │   (FastAPI daemon)               │
│                     │ ◄────────────────────────── │                                  │
└─────────────────────┘                             └────────────┬─────────────────────┘
                                                                 │
                              ┌──────────────────────────────────┼──────────────────────┐
                              │                                  │                      │
                              ▼                                  ▼                      ▼
                     ┌────────────────┐             ┌─────────────────────┐   ┌─────────────────┐
                     │  Ollama        │             │  SQLite (wiki.db)   │   │  Markdown Files │
                     │  glm-4.7-flash │             │  FTS5 index         │   │  (Obsidian vault│
                     │  :11434        │             │  QA + pages tables  │   │   compatible)   │
                     └────────────────┘             └─────────────────────┘   └─────────────────┘
```

**Core contract:**
- Input: generic Q/A JSON (any LLM, any client)
- Output (ingest): `202 Accepted` — pipeline runs async, caller is not blocked
- Output (query): ranked JSON list of matching wiki entries

---

## 2. Pipeline Architecture

### 2.1 Ingest Pipeline (real-time, per Q/A pair)

```
POST /ingest
    │
    ▼
[1] Validate Schema          ← Pydantic model, reject malformed input fast
    │
    ▼
[2] Summarize via Ollama     ← glm-4.7-flash: compress Q+A → 1–3 sentence atom
    │                           Prompt: extract core claim, strip filler
    ▼
[3] Write Raw JSON           ← raw/qa/<YYYY-MM-DD>/<slug>.json  (immutable)
    │
    ▼
[4] Generate Wiki Page       ← glm-4.7-flash: write/update markdown page
    │                           - New topic → create wiki/concepts/<slug>.md
    │                           - Existing topic → append/patch existing page
    ▼
[5] Update SQLite Index      ← Insert/upsert into pages + qa_pairs tables
    │                           FTS5 index auto-updated on INSERT
    ▼
[6] Update index.md + log.md ← Deterministic append (no LLM needed)
    │
    ▼
[7] Return 202               ← Pipeline done; caller already unblocked at step 1
```

Steps 2–6 run in a background `asyncio` task queue (non-blocking ingest). The HTTP response returns immediately after schema validation.

### 2.2 Query Pipeline (synchronous)

```
GET /query?q=<keyword>&limit=5
    │
    ▼
[1] Tokenize query           ← strip stopwords, extract keywords
    │
    ▼
[2] FTS5 Search              ← SQLite: MATCH query over pages + qa_pairs
    │                           Ranks by BM25 score (built into SQLite FTS5)
    ▼
[3] Load page snippets       ← Read top-k markdown files for context
    │
    ▼
[4] Return ranked JSON       ← [{title, snippet, path, score, tags, updated}]
```

No LLM in the query path by default. Fast, deterministic, token-free.  
Optional: add a `?summarize=true` param that passes top-k snippets through glm-4.7-flash for a synthesized answer.

---

## 3. API Contract

### 3.1 `POST /ingest`

**Request body:**
```json
{
  "question": "What is the attention mechanism in transformers?",
  "answer": "Attention allows the model to weight the relevance of each token when predicting the next one. Scaled dot-product attention divides by √d_k to prevent gradient vanishing.",
  "source": "claude-chat",
  "session_id": "sess_abc123",
  "tags": ["transformers", "attention", "nlp"],
  "timestamp": "2026-04-21T10:00:00Z"
}
```

**Fields:**

| Field | Type | Required | Notes |
|---|---|---|---|
| `question` | string | ✅ | The user's question |
| `answer` | string | ✅ | The LLM's response |
| `source` | string | ❌ | Origin client label (default: `"unknown"`) |
| `session_id` | string | ❌ | Groups Q/A from the same chat session |
| `tags` | string[] | ❌ | Hints for topic routing (LLM can override) |
| `timestamp` | ISO8601 | ❌ | Defaults to server receive time |

**Response:**
```json
{
  "status": "accepted",
  "ingest_id": "ing_2026-04-21_00042",
  "queued_at": "2026-04-21T10:00:01Z"
}
```
HTTP `202 Accepted`. Pipeline runs async.

---

### 3.2 `GET /query?q=<keyword>`

**Params:**

| Param | Type | Default | Notes |
|---|---|---|---|
| `q` | string | required | Keyword(s); multi-word = phrase match |
| `limit` | int | 5 | Max results returned |
| `type` | string | `all` | Filter by page type: `concept`, `entity`, `source`, `synthesis` |
| `summarize` | bool | `false` | Run results through glm-4.7-flash for synthesis |

**Response:**
```json
{
  "query": "attention mechanism",
  "results": [
    {
      "title": "Attention Mechanism",
      "type": "concept",
      "path": "wiki/concepts/attention-mechanism.md",
      "snippet": "Attention allows the model to weight token relevance...",
      "tags": ["transformers", "attention", "nlp"],
      "score": 12.4,
      "updated": "2026-04-21T10:00:05Z",
      "inbound_links": 3
    }
  ],
  "total": 1,
  "summarized_answer": null
}
```

---

### 3.3 `GET /health`

```json
{
  "status": "ok",
  "ollama": "reachable",
  "db": "ok",
  "queue_depth": 0,
  "wiki_pages": 42,
  "qa_pairs": 187
}
```

### 3.4 `GET /stats`

```json
{
  "total_ingests": 187,
  "total_wiki_pages": 42,
  "top_tags": [["transformers", 14], ["python", 9]],
  "last_ingest": "2026-04-21T10:00:05Z",
  "orphan_pages": 2
}
```

---

## 4. Data Models

### 4.1 Raw Q/A JSON (immutable, written once)

Path: `raw/qa/YYYY-MM-DD/<slug>.json`

```json
{
  "ingest_id": "ing_2026-04-21_00042",
  "received_at": "2026-04-21T10:00:01Z",
  "source": "claude-chat",
  "session_id": "sess_abc123",
  "original": {
    "question": "What is the attention mechanism in transformers?",
    "answer": "Attention allows the model to weight..."
  },
  "summary": {
    "atom": "Scaled dot-product attention weights token relevance by dividing dot products by √d_k, preventing gradient vanishing in high-dimensional spaces.",
    "key_claims": [
      "attention weights token relevance per prediction",
      "scaling by 1/√d_k prevents gradient vanishing"
    ],
    "detected_topics": ["attention", "transformers", "gradients"],
    "detected_entities": []
  },
  "wiki_page": "wiki/concepts/attention-mechanism.md",
  "model": "glm-4.7-flash:latest",
  "tags": ["transformers", "attention", "nlp"]
}
```

### 4.2 SQLite Schema (`wiki.db`)

```sql
-- Pages table (one row per wiki markdown file)
CREATE TABLE pages (
  id          TEXT PRIMARY KEY,        -- slug, e.g. "attention-mechanism"
  title       TEXT NOT NULL,
  type        TEXT NOT NULL,           -- concept | entity | source | synthesis
  path        TEXT NOT NULL UNIQUE,    -- relative path: wiki/concepts/...
  tags        TEXT,                    -- JSON array as text
  confidence  TEXT DEFAULT 'medium',  -- high | medium | low
  created_at  TEXT NOT NULL,
  updated_at  TEXT NOT NULL,
  inbound_links INTEGER DEFAULT 0,
  content     TEXT NOT NULL            -- full markdown content (for FTS)
);

-- Q/A pairs table
CREATE TABLE qa_pairs (
  id          TEXT PRIMARY KEY,        -- ingest_id
  page_id     TEXT REFERENCES pages(id),
  question    TEXT NOT NULL,
  answer      TEXT NOT NULL,
  atom        TEXT NOT NULL,           -- LLM-generated summary
  tags        TEXT,                    -- JSON array
  source      TEXT,
  session_id  TEXT,
  created_at  TEXT NOT NULL
);

-- Link graph (wikilinks adjacency)
CREATE TABLE wiki_links (
  from_page   TEXT NOT NULL,
  to_page     TEXT NOT NULL,
  PRIMARY KEY (from_page, to_page)
);

-- FTS5 virtual table (BM25 search over pages)
CREATE VIRTUAL TABLE pages_fts USING fts5(
  title,
  content,
  tags,
  content=pages,
  content_rowid=rowid
);

-- FTS5 over Q/A pairs
CREATE VIRTUAL TABLE qa_fts USING fts5(
  question,
  answer,
  atom,
  tags,
  content=qa_pairs,
  content_rowid=rowid
);

-- Auto-sync triggers
CREATE TRIGGER pages_ai AFTER INSERT ON pages BEGIN
  INSERT INTO pages_fts(rowid, title, content, tags)
  VALUES (new.rowid, new.title, new.content, new.tags);
END;

CREATE TRIGGER pages_au AFTER UPDATE ON pages BEGIN
  INSERT INTO pages_fts(pages_fts, rowid, title, content, tags)
  VALUES ('delete', old.rowid, old.title, old.content, old.tags);
  INSERT INTO pages_fts(rowid, title, content, tags)
  VALUES (new.rowid, new.title, new.content, new.tags);
END;
```

### 4.3 Wiki Page Format (Markdown + YAML frontmatter)

```markdown
---
id: attention-mechanism
title: "Attention Mechanism"
type: concept
tags: [transformers, attention, nlp]
confidence: medium
created: 2026-04-21
updated: 2026-04-21
sources: ["ing_2026-04-21_00042"]
inbound_links: 3
---

# Attention Mechanism

Scaled dot-product attention weights token relevance by dividing dot
products by √d_k, preventing gradient vanishing in high-dimensional spaces.

## Key Claims

- Attention weights token relevance per prediction step
- Scaling by 1/√d_k prevents gradient vanishing (from [[transformers]])

## Sources

- `ing_2026-04-21_00042` — 2026-04-21 via claude-chat
```

---

## 5. Directory Structure

```
llm-wiki/
├── server/                         # Middleware daemon
│   ├── main.py                     # FastAPI app, lifespan, routes
│   ├── pipeline/
│   │   ├── ingest.py               # Ingest pipeline orchestrator
│   │   ├── summarize.py            # Ollama summarization step
│   │   ├── wiki_writer.py          # Markdown page create/update
│   │   ├── index_updater.py        # SQLite + index.md + log.md
│   │   └── query.py                # FTS5 query + optional synthesis
│   ├── models/
│   │   ├── request.py              # Pydantic: IngestRequest, QueryResponse
│   │   └── qa.py                   # Pydantic: QAPair, Atom, WikiPage
│   ├── db/
│   │   ├── database.py             # SQLite connection pool (aiosqlite)
│   │   └── migrations/
│   │       └── 001_init.sql
│   ├── ollama/
│   │   └── client.py               # Ollama HTTP wrapper with retry
│   └── config.py                   # Settings (pydantic-settings, .env)
│
├── wiki/                           # Obsidian vault (LLM-written)
│   ├── AGENTS.md                   # Schema/workflow config
│   ├── index.md                    # Content catalog
│   ├── log.md                      # Append-only ops log
│   ├── concepts/
│   ├── entities/
│   ├── sources/
│   └── synthesis/
│
├── raw/
│   └── qa/
│       └── YYYY-MM-DD/             # Immutable raw Q/A JSON
│           └── <slug>.json
│
├── db/
│   └── wiki.db                     # SQLite database
│
├── config/
│   └── .env                        # OLLAMA_HOST, WIKI_DIR, DB_PATH, etc.
│
├── pyproject.toml                  # uv / ruff / dependencies
├── AGENTS.md                       # Root-level (OpenCode/Codex readable)
└── README.md
```

---

## 6. Key Implementation Details

### 6.1 Summarization Prompt (glm-4.7-flash)

```python
SUMMARIZE_PROMPT = """\
You are a knowledge distiller. Given a Q/A pair from a chat session, extract the core knowledge atom.

Rules:
- Output exactly 1-3 sentences. No filler, no hedging.
- Extract only verifiable claims, not opinions.
- Identify 2-5 topic tags (lowercase, hyphenated).
- Identify any named entities (people, tools, systems).
- Return JSON only. No markdown. No preamble.

Output schema:
{
  "atom": "<1-3 sentence distilled claim>",
  "key_claims": ["<claim 1>", "<claim 2>"],
  "detected_topics": ["<tag1>", "<tag2>"],
  "detected_entities": ["<EntityName>"]
}

Q: {question}
A: {answer}
"""
```

### 6.2 Wiki Page Update Strategy

Topic routing logic (deterministic, before LLM involvement):

```
Detected topic exists in SQLite pages?
    YES → load existing .md file → LLM appends/revises content
    NO  → LLM creates new page from atom + claims
```

Conflict/contradiction detection: if the new atom contradicts an existing key claim on the page (detected by simple string diff + LLM check), append a `> ⚠️ Contradiction noted:` blockquote rather than silently overwriting. This is the single most important correctness guardrail.

### 6.3 Async Queue (non-blocking ingest)

```python
# main.py — simplified
from asyncio import Queue

ingest_queue: Queue = Queue()

@app.post("/ingest", status_code=202)
async def ingest(req: IngestRequest):
    ingest_id = generate_id()
    await ingest_queue.put((ingest_id, req))
    return {"status": "accepted", "ingest_id": ingest_id}

@app.on_event("startup")
async def start_worker():
    asyncio.create_task(pipeline_worker(ingest_queue))
```

Queue depth is observable via `/health`. If queue grows unbounded, add a second worker (config: `WORKER_COUNT=2`).

### 6.4 Ollama Client (with retry + timeout)

```python
async def call_ollama(prompt: str, model: str = "glm-4.7-flash:latest") -> str:
    async with httpx.AsyncClient(timeout=60.0) as client:
        for attempt in range(3):
            try:
                r = await client.post(
                    f"{OLLAMA_HOST}/api/generate",
                    json={"model": model, "prompt": prompt, "stream": False}
                )
                r.raise_for_status()
                return r.json()["response"]
            except (httpx.TimeoutException, httpx.HTTPStatusError) as e:
                if attempt == 2:
                    raise
                await asyncio.sleep(2 ** attempt)
```

### 6.5 FTS5 Query

```python
async def search_wiki(query: str, limit: int = 5) -> list[dict]:
    terms = " OR ".join(query.strip().split())  # multi-keyword OR
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
            SELECT p.title, p.type, p.path, p.tags, p.updated_at,
                   snippet(pages_fts, 1, '<b>', '</b>', '...', 20) as snippet,
                   bm25(pages_fts) as score
            FROM pages_fts
            JOIN pages p ON pages_fts.rowid = p.rowid
            WHERE pages_fts MATCH ?
            ORDER BY score
            LIMIT ?
        """, (terms, limit))
        return [dict(zip([c[0] for c in cur.description], row))
                async for row in cur]
```

SQLite FTS5's built-in `bm25()` ranking is used directly — no external library needed.

---

## 7. Tech Stack

| Component | Choice | Why |
|---|---|---|
| HTTP framework | FastAPI + uvicorn | async-native, Pydantic validation, fast |
| LLM | glm-4.7-flash via Ollama | local, fast, cheap per token |
| Ollama client | httpx (async) | native async, timeout control |
| Database | SQLite + FTS5 (aiosqlite) | zero infra, BM25 built-in, reliable |
| Wiki format | Markdown + YAML frontmatter | Obsidian-compatible, git-native |
| Config | pydantic-settings + .env | type-safe, 12-factor |
| Package manager | uv | fast, lockfile, modern |
| Linter | ruff | single tool for format + lint |
| Testing | pytest + pytest-asyncio | async test support |

**No external vector DB in this phase.** SQLite FTS5 with BM25 handles keyword retrieval at personal/small-team scale (hundreds of pages). ChromaDB can be added in a later phase for semantic (embedding) retrieval.

---

## 8. Configuration (`.env`)

```dotenv
# Ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=glm-4.7-flash:latest
OLLAMA_TIMEOUT=60

# Paths
WIKI_DIR=./wiki
RAW_DIR=./raw/qa
DB_PATH=./db/wiki.db

# Server
HOST=0.0.0.0
PORT=8000
WORKER_COUNT=1

# Pipeline
MAX_ATOM_SENTENCES=3
MAX_QUEUE_SIZE=100
INGEST_LOG_LEVEL=INFO
```

---

## 9. Implementation Phases

### Phase 1 — Skeleton (Day 1–2)
- [x] FastAPI app with `/ingest`, `/query`, `/health` stubs
- [x] Pydantic request/response models
- [x] SQLite init + migrations (001_init.sql)
- [x] Ollama client wrapper with retry
- [x] `.env` + `config.py`

### Phase 2 — Ingest Pipeline (Day 3–5)
- [x] Summarize step: prompt → Ollama → parse JSON atom
- [x] Raw JSON writer (`raw/qa/<date>/<slug>.json`)
- [x] Wiki page writer: create new `.md` or patch existing
- [x] SQLite upsert: pages + qa_pairs + FTS5 triggers
- [x] `index.md` + `log.md` append

### Phase 3 — Query (Day 6–7)
- [x] FTS5 search with BM25 ranking
- [x] Snippet extraction
- [x] `?summarize=true` path through glm-4.7-flash
- [x] `/stats` endpoint

### Phase 4 — Hardening (Day 8–10)
- [x] Contradiction detection in wiki page update
- [x] Link graph maintenance (`wiki_links` table)
- [x] Orphan page detection in `/stats`
- [x] Error handling + dead-letter queue for failed ingests
- [x] Unit tests for pipeline steps
- [x] Integration test: POST → GET roundtrip

---

## 10. Key Design Decisions & Trade-offs

| Decision | Choice | Alternative | Why |
|---|---|---|---|
| Ingest blocking | Async queue, 202 response | Sync, wait for pipeline | LLM calls are slow (1–5s); caller shouldn't block |
| Search | SQLite FTS5 BM25 | ChromaDB + embeddings | No infra, deterministic, fast; add semantic later |
| Wiki format | Markdown + YAML | Pure DB | Human-readable, Obsidian-compatible, git-native |
| Model | glm-4.7-flash only | Split model routing | Simplicity first; qwen3.5 can replace for synthesis later |
| Raw layer | Immutable JSON | Overwrite in DB | Source of truth; enables rollback (`git revert`) |
| Contradiction | Append blockquote | Silent overwrite | Preserves provenance; human resolves |

---

## 11. Runbook

```bash
# Install
uv sync

# Init DB
python -m server.db.database init

# Run daemon
uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload

# Ingest a Q/A pair
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"question": "What is RAG?", "answer": "RAG is retrieval-augmented generation..."}'

# Query
curl "http://localhost:8000/query?q=RAG&limit=3"

# Health
curl http://localhost:8000/health
```

---

## 12. Open Questions (Decide Before Phase 2)

1. **Topic routing threshold:** When does glm-4.7-flash decide "this is the same topic as an existing page" vs "create a new page"? Strategy options: slug match on detected_topics, FTS5 self-query, or always create + merge on lint. Recommendation: FTS5 self-query first (if score > threshold → update existing).

2. **Session grouping:** Should Q/A pairs from the same `session_id` be co-located on the same wiki page, or always routed by topic? Session-based grouping = easier rollback; topic-based = better cross-referencing.

3. **Wiki page granularity:** One page per topic (broad, grows over time) or one page per ingest (many small pages, graph-linked)? Recommendation: one page per topic, with a `sources` list in frontmatter linking back to raw Q/A.

4. **Contradiction policy:** Auto-append warning blockquote (current plan) vs. flag in SQLite for human review vs. call LLM to resolve. The blockquote approach is the safest for v1.

5. **Lint schedule:** Manual (`GET /lint`) or scheduled (cron every N hours)? Cron avoids accumulating orphans, but adds complexity. Recommendation: manual for v1, add cron in Phase 4.