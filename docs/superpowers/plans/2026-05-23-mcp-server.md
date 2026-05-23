# MCP Server Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose mem-weaver wiki memory to IDEs via a standalone stdio FastMCP server with four tools, backed by a shared `memory_api` service layer used by both MCP and HTTP routes.

**Architecture:** Extract `server/services/memory_api.py` from existing route logic in `main.py`. Add `server/mcp_server.py` (FastMCP + lifespan for DB init and ingest worker). MCP tools call the same service functions as HTTP; no HTTP proxy.

**Tech Stack:** Python 3.12, FastMCP 2.x+, FastAPI, aiosqlite, existing pipeline modules (`query_search`, `ingest_worker`, `embedder`)

**Spec:** `docs/superpowers/specs/2026-05-23-mcp-server-design.md`

---

## File Structure

| File | Responsibility |
|------|----------------|
| `server/services/memory_api.py` | Shared async API: search, ingest, get page, stats |
| `server/mcp_server.py` | FastMCP stdio entrypoint, lifespan, 4 tools |
| `server/main.py` | Thin HTTP routes delegating to `memory_api` |
| `tests/test_memory_api.py` | Unit tests for service layer |
| `tests/test_mcp_server.py` | In-process FastMCP smoke tests |
| `.cursor/mcp.json.example` | Example Cursor MCP config |
| `README.md` | MCP setup section |

---

### Task 1: Add FastMCP dependency

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add fastmcp to requirements**

Append to `requirements.txt`:

```
fastmcp>=2.0,<4
```

- [ ] **Step 2: Install and verify import**

Run:

```bash
./venv/bin/pip install 'fastmcp>=2.0,<4'
./venv/bin/python -c "from fastmcp import FastMCP; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "chore: add fastmcp dependency for MCP server"
```

---

### Task 2: `get_wiki_page` service function

**Files:**
- Create: `server/services/memory_api.py`
- Create: `tests/test_memory_api.py`

- [ ] **Step 1: Write failing tests for get_wiki_page**

Create `tests/test_memory_api.py`:

```python
"""Unit tests for server.services.memory_api."""

from pathlib import Path

import pytest

from server.config import Settings
from server.services import memory_api


@pytest.fixture
def isolated_settings(tmp_path: Path) -> Settings:
    base = tmp_path / "mw"
    base.mkdir(parents=True, exist_ok=True)
    wiki = base / "wiki"
    wiki.mkdir(parents=True, exist_ok=True)
    return Settings(
        db_path=base / "t.db",
        wiki_dir=wiki,
        raw_dir=base / "raw",
        dlq_dir=base / "failed",
        ollama_host="http://127.0.0.1:9",
        ollama_model="test-model",
        ollama_timeout=5.0,
    )


@pytest.mark.asyncio
async def test_get_wiki_page_found(isolated_settings: Settings) -> None:
    slug = "concepts/hybrid-search"
    path = isolated_settings.wiki_dir / f"{slug}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# Hybrid Search\n", encoding="utf-8")

    result = await memory_api.get_wiki_page(isolated_settings, slug)

    assert result["slug"] == slug
    assert "Hybrid Search" in result["content"]


@pytest.mark.asyncio
async def test_get_wiki_page_missing(isolated_settings: Settings) -> None:
    result = await memory_api.get_wiki_page(isolated_settings, "concepts/missing")

    assert result["slug"] == "concepts/missing"
    assert result["content"] == ""
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./venv/bin/pytest tests/test_memory_api.py::test_get_wiki_page_found tests/test_memory_api.py::test_get_wiki_page_missing -v`

Expected: FAIL — `ModuleNotFoundError` or `AttributeError: get_wiki_page`

- [ ] **Step 3: Implement get_wiki_page**

Create `server/services/memory_api.py`:

```python
"""Shared wiki memory operations for HTTP routes and MCP tools."""

from __future__ import annotations

from pathlib import Path

from server.config import Settings


async def get_wiki_page(settings: Settings, slug: str) -> dict[str, str]:
    """Read wiki markdown by slug. Returns empty content if not found."""
    article_path = Path(settings.wiki_dir) / f"{slug}.md"
    if article_path.exists():
        content = article_path.read_text(encoding="utf-8")
    else:
        content = ""
    return {"slug": slug, "content": content}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `./venv/bin/pytest tests/test_memory_api.py::test_get_wiki_page_found tests/test_memory_api.py::test_get_wiki_page_missing -v`

Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add server/services/memory_api.py tests/test_memory_api.py
git commit -m "feat: add get_wiki_page to memory_api service layer"
```

---

### Task 3: `search_wiki` service function

**Files:**
- Modify: `server/services/memory_api.py`
- Modify: `tests/test_memory_api.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_memory_api.py`:

```python
import asyncio

import pytest

from server.db.database import init_db
from server.models.api import QueryMode


@pytest.fixture
def db_settings(tmp_path: Path) -> Settings:
    base = tmp_path / "mw"
    base.mkdir(parents=True, exist_ok=True)
    s = Settings(
        db_path=base / "t.db",
        wiki_dir=base / "wiki",
        raw_dir=base / "raw",
        dlq_dir=base / "failed",
        ollama_host="http://127.0.0.1:9",
        ollama_model="test-model",
        ollama_timeout=5.0,
    )
    asyncio.run(init_db(s))
    return s


async def _seed_page(settings: Settings, page_id: str, title: str, content: str) -> None:
    import aiosqlite

    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute(
            """
            INSERT INTO pages (id, title, type, path, tags, confidence,
                               created_at, updated_at, inbound_links, content)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                page_id,
                title,
                "concept",
                f"wiki/concepts/{page_id}.md",
                '["search"]',
                "medium",
                "2026-01-01",
                "2026-01-01",
                0,
                content,
            ],
        )
        await db.execute("DELETE FROM pages_fts WHERE page_id = ?", [page_id])
        await db.execute(
            "INSERT INTO pages_fts (page_id, title, content, tags) VALUES (?, ?, ?, ?)",
            [page_id, title, content, "search"],
        )
        await db.commit()


@pytest.mark.asyncio
async def test_search_wiki_empty_query(db_settings: Settings) -> None:
    result = await memory_api.search_wiki(db_settings, "   ")

    assert "error" in result
    assert "empty" in result["error"].lower()


@pytest.mark.asyncio
async def test_search_wiki_keyword(db_settings: Settings) -> None:
    await _seed_page(
        db_settings,
        "fastapi-patterns",
        "FastAPI Patterns",
        "Use dependency injection in FastAPI routes.",
    )

    result = await memory_api.search_wiki(
        db_settings,
        "FastAPI",
        limit=5,
        mode=QueryMode.KEYWORD,
    )

    assert result["error"] is None
    assert result["total"] >= 1
    assert any("fastapi" in (r.get("title") or "").lower() for r in result["results"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./venv/bin/pytest tests/test_memory_api.py::test_search_wiki_empty_query tests/test_memory_api.py::test_search_wiki_keyword -v`

Expected: FAIL — `search_wiki` not defined

- [ ] **Step 3: Implement search_wiki**

Add to `server/services/memory_api.py`:

```python
import logging
from typing import Any

from server.models.api import QueryMode
from server.pipeline.embedder import embed_text
from server.pipeline.query_search import search_hybrid, search_pages
from server.pipeline.search_semantic import search_semantic

logger = logging.getLogger(__name__)

MCP_SEARCH_LIMIT_MAX = 20


async def search_wiki(
    settings: Settings,
    query: str,
    *,
    limit: int = 5,
    mode: QueryMode = QueryMode.HYBRID,
) -> dict[str, Any]:
    """Search wiki pages. Returns result dict or {\"error\": ...} on validation failure."""
    q = query.strip()
    if not q:
        return {"error": "query must not be empty"}

    clamped = max(1, min(limit, MCP_SEARCH_LIMIT_MAX))

    try:
        if mode == QueryMode.KEYWORD:
            rows = await search_pages(settings, q, clamped)
        elif mode == QueryMode.SEMANTIC:
            query_vec = await embed_text(settings, q)
            rows = await search_semantic(settings, query_vec, clamped)
        else:
            rows = await search_hybrid(settings, q, clamped)
    except Exception:
        logger.exception("search_wiki failed for query=%r mode=%s", q, mode)
        return {"error": "search failed", "detail": "unexpected error during search"}

    slim_results = [
        {
            "title": r.get("title"),
            "path": r.get("path"),
            "snippet": r.get("snippet"),
            "score": r.get("score"),
            "tags": r.get("tags"),
        }
        for r in rows
    ]
    return {
        "error": None,
        "query": q,
        "mode": mode.value,
        "total": len(slim_results),
        "results": slim_results,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `./venv/bin/pytest tests/test_memory_api.py::test_search_wiki_empty_query tests/test_memory_api.py::test_search_wiki_keyword -v`

Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add server/services/memory_api.py tests/test_memory_api.py
git commit -m "feat: add search_wiki to memory_api service layer"
```

---

### Task 4: `enqueue_ingest` service function

**Files:**
- Modify: `server/services/memory_api.py`
- Modify: `tests/test_memory_api.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_memory_api.py`:

```python
import asyncio
from datetime import datetime, timezone

from server.pipeline.ingest_worker import IngestJob


@pytest.mark.asyncio
async def test_enqueue_ingest_accepted(isolated_settings: Settings) -> None:
    queue: asyncio.Queue[IngestJob] = asyncio.Queue(maxsize=10)

    result = await memory_api.enqueue_ingest(
        isolated_settings,
        queue,
        question="What is MCP?",
        answer="Model Context Protocol exposes tools to LLMs.",
        source="test",
        tags=["mcp"],
    )

    assert result["status"] == "accepted"
    assert result["ingest_id"].startswith("ing_")
    assert queue.qsize() == 1
    job = queue.get_nowait()
    assert job.question == "What is MCP?"


@pytest.mark.asyncio
async def test_enqueue_ingest_queue_full(isolated_settings: Settings) -> None:
    queue: asyncio.Queue[IngestJob] = asyncio.Queue(maxsize=0)

    with pytest.raises(memory_api.IngestQueueFullError) as exc:
        await memory_api.enqueue_ingest(
            isolated_settings,
            queue,
            question="Q",
            answer="A",
        )

    assert exc.value.queue_depth == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./venv/bin/pytest tests/test_memory_api.py::test_enqueue_ingest_accepted tests/test_memory_api.py::test_enqueue_ingest_queue_full -v`

Expected: FAIL

- [ ] **Step 3: Implement enqueue_ingest**

Add to `server/services/memory_api.py`:

```python
import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from server.pipeline.ingest_worker import IngestJob


class IngestQueueFullError(Exception):
    """Raised when the ingest asyncio queue is at capacity."""

    def __init__(self, queue_depth: int) -> None:
        self.queue_depth = queue_depth
        super().__init__(f"ingest queue is full (depth={queue_depth})")


def make_ingest_id() -> str:
    return f"ing_{datetime.now(timezone.utc).strftime('%Y%m%d')}_{uuid4().hex[:8]}"


async def enqueue_ingest(
    settings: Settings,
    queue: asyncio.Queue[IngestJob],
    *,
    question: str,
    answer: str,
    source: str = "mcp",
    tags: list[str] | None = None,
    session_id: str | None = None,
    received_at: datetime | None = None,
) -> dict[str, str]:
    """Enqueue a Q/A pair for async wiki compilation."""
    _ = settings  # reserved for future validation hooks
    q = question.strip()
    a = answer.strip()
    if not q or not a:
        raise ValueError("question and answer must not be empty")

    received = received_at or datetime.now(timezone.utc)
    if received.tzinfo is None:
        received = received.replace(tzinfo=timezone.utc)

    ingest_id = make_ingest_id()
    job = IngestJob(
        ingest_id=ingest_id,
        question=q,
        answer=a,
        source=source,
        session_id=session_id,
        tags=tags or [],
        received_at=received,
    )
    try:
        queue.put_nowait(job)
    except asyncio.QueueFull as err:
        raise IngestQueueFullError(queue.qsize()) from err

    return {
        "status": "accepted",
        "ingest_id": ingest_id,
        "message": (
            "Queued for wiki compilation. "
            "Page will appear after Ollama processing (~30-60s)."
        ),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `./venv/bin/pytest tests/test_memory_api.py::test_enqueue_ingest_accepted tests/test_memory_api.py::test_enqueue_ingest_queue_full -v`

Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add server/services/memory_api.py tests/test_memory_api.py
git commit -m "feat: add enqueue_ingest to memory_api service layer"
```

---

### Task 5: `get_wiki_stats` service function

**Files:**
- Modify: `server/services/memory_api.py`
- Modify: `tests/test_memory_api.py`

- [ ] **Step 1: Write failing test**

Append to `tests/test_memory_api.py`:

```python
import aiosqlite


@pytest.mark.asyncio
async def test_get_wiki_stats(db_settings: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
    async with aiosqlite.connect(db_settings.db_path) as db:
        await db.execute(
            """
            INSERT INTO pages (id, title, type, path, tags, confidence,
                               created_at, updated_at, inbound_links, content)
            VALUES ('p1', 'One', 'concept', 'wiki/concepts/one.md', '[]',
                    'medium', '2026-01-01', '2026-01-01', 0, 'body')
            """
        )
        await db.execute(
            """
            INSERT INTO qa_pairs (id, question, answer, source, session_id, tags, created_at)
            VALUES ('q1', 'Q?', 'A.', 'test', NULL, '["tag"]', '2026-01-02')
            """
        )
        await db.commit()

    async def fake_unreachable(*args: object, **kwargs: object) -> None:
        raise ConnectionError("down")

    monkeypatch.setattr("server.services.memory_api._ollama_reachable", fake_unreachable)

    stats = await memory_api.get_wiki_stats(db_settings, queue=None)

    assert stats["wiki_pages"] == 1
    assert stats["qa_pairs"] == 1
    assert stats["ollama"] == "unreachable"
    assert stats["queue_depth"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/bin/pytest tests/test_memory_api.py::test_get_wiki_stats -v`

Expected: FAIL

- [ ] **Step 3: Implement get_wiki_stats**

Add to `server/services/memory_api.py`:

```python
import asyncio

import aiosqlite
import httpx

from server.pipeline.ingest_worker import IngestJob


async def _ollama_reachable(settings: Settings) -> str:
    try:
        headers: dict[str, str] = {}
        if settings.ollama_api_key:
            headers["Authorization"] = f"Bearer {settings.ollama_api_key}"
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(
                f"{settings.ollama_host.rstrip('/')}/api/tags",
                headers=headers,
            )
            r.raise_for_status()
        return "reachable"
    except Exception:
        return "unreachable"


async def get_wiki_stats(
    settings: Settings,
    queue: asyncio.Queue[IngestJob] | None = None,
) -> dict[str, Any]:
    """Aggregate wiki counters plus Ollama reachability and queue depth."""
    async with aiosqlite.connect(settings.db_path) as db:
        cur = await db.execute("SELECT COUNT(*) FROM qa_pairs")
        total_ingests = int((await cur.fetchone())[0])
        cur = await db.execute("SELECT COUNT(*) FROM pages")
        total_wiki_pages = int((await cur.fetchone())[0])
        cur = await db.execute("SELECT MAX(created_at) FROM qa_pairs")
        row = await cur.fetchone()
        last_ingest = str(row[0]) if row and row[0] else None
        cur = await db.execute(
            """
            SELECT COUNT(*) FROM pages p
            WHERE NOT EXISTS (
                SELECT 1 FROM wiki_links w WHERE w.to_page = p.id
            )
            """
        )
        orphan_pages = int((await cur.fetchone())[0])
        cur = await db.execute(
            """
            SELECT j.value AS tag, COUNT(*) AS c
            FROM qa_pairs
            CROSS JOIN json_each(qa_pairs.tags) AS j
            WHERE json_valid(qa_pairs.tags)
            GROUP BY j.value
            ORDER BY c DESC
            LIMIT 15
            """
        )
        tag_rows = await cur.fetchall()
        top_tags: list[list[str | int]] = [[str(r[0]), int(r[1])] for r in tag_rows]

    ollama = await _ollama_reachable(settings)
    queue_depth = queue.qsize() if queue is not None else 0

    return {
        "wiki_pages": total_wiki_pages,
        "qa_pairs": total_ingests,
        "orphan_pages": orphan_pages,
        "top_tags": top_tags,
        "last_ingest": last_ingest,
        "ollama": ollama,
        "queue_depth": queue_depth,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./venv/bin/pytest tests/test_memory_api.py::test_get_wiki_stats -v`

Expected: PASS

- [ ] **Step 5: Run full memory_api test suite**

Run: `./venv/bin/pytest tests/test_memory_api.py -v`

Expected: PASS (all tests)

- [ ] **Step 6: Commit**

```bash
git add server/services/memory_api.py tests/test_memory_api.py
git commit -m "feat: add get_wiki_stats to memory_api service layer"
```

---

### Task 6: Refactor `main.py` to delegate to `memory_api`

**Files:**
- Modify: `server/main.py`

- [ ] **Step 1: Refactor ingest, query, wiki, stats routes**

Replace inline logic in `server/main.py` with delegations. Key changes:

```python
from server.services import memory_api
from server.services.memory_api import IngestQueueFullError, make_ingest_id
```

**`POST /ingest`** — replace body with:

```python
@app.post("/ingest", response_model=IngestResponse, status_code=202)
async def ingest(payload: IngestPayload) -> IngestResponse:
    cfg = app.state.settings
    received = payload.timestamp or datetime.now(timezone.utc)
    if received.tzinfo is None:
        received = received.replace(tzinfo=timezone.utc)
    try:
        result = await memory_api.enqueue_ingest(
            cfg,
            app.state.ingest_queue,
            question=payload.question,
            answer=payload.answer,
            source=payload.source or "unknown",
            tags=payload.tags,
            session_id=payload.session_id,
            received_at=received,
        )
    except IngestQueueFullError as err:
        raise HTTPException(status_code=503, detail="ingest queue is full") from err
    return IngestResponse(
        status="accepted",
        ingest_id=result["ingest_id"],
        queued_at=datetime.now(timezone.utc),
    )
```

**`GET /query`** — replace search block with:

```python
    payload = await memory_api.search_wiki(cfg, q, limit=limit, mode=mode)
    if payload.get("error"):
        raise HTTPException(status_code=400, detail=payload["error"])
    rows = payload["results"]
    # keep existing summarize block unchanged, using rows
    return QueryResponse(
        query=payload["query"],
        mode=mode,
        results=rows,
        total=payload["total"],
        summarized_answer=summarized,
    )
```

Note: HTTP `/query` returns full row dicts from search functions today. Update `search_wiki` to return full rows for HTTP compatibility — remove the `slim_results` mapping and return `rows` directly in the success payload. MCP tool handler can slim fields at the MCP layer instead.

**`GET /wiki/{slug}`:**

```python
    data = await memory_api.get_wiki_page(cfg, slug)
    return WikiResponse(**data)
```

**`GET /stats`:**

```python
    data = await memory_api.get_wiki_stats(cfg, app.state.ingest_queue)
    return StatsResponse(
        total_ingests=data["qa_pairs"],
        total_wiki_pages=data["wiki_pages"],
        top_tags=data["top_tags"],
        last_ingest=data["last_ingest"],
        orphan_pages=data["orphan_pages"],
    )
```

**`POST /chat` background ingest** — replace inline job creation with:

```python
            try:
                await memory_api.enqueue_ingest(
                    cfg,
                    app.state.ingest_queue,
                    question=req.question.strip(),
                    answer=full_answer.strip(),
                    source="chat",
                    tags=[topic],
                )
            except Exception:
                logger.exception("failed to enqueue background compilation for chat")
```

Remove unused imports: `Path` (if wiki route no longer uses it), direct `search_*` imports if unused, `_make_ingest_id` (use `make_ingest_id` only if still needed elsewhere — chat no longer needs it).

- [ ] **Step 2: Adjust search_wiki to return full pipeline rows**

In `server/services/memory_api.py`, change success return to use `rows` directly:

```python
    return {
        "error": None,
        "query": q,
        "mode": mode.value,
        "total": len(rows),
        "results": rows,
    }
```

- [ ] **Step 3: Run existing test suite**

Run: `./venv/bin/pytest tests/ -v`

Expected: all tests PASS (fix any regressions)

- [ ] **Step 4: Commit**

```bash
git add server/main.py server/services/memory_api.py
git commit -m "refactor: delegate HTTP routes to memory_api service layer"
```

---

### Task 7: FastMCP server with four tools

**Files:**
- Create: `server/mcp_server.py`

- [ ] **Step 1: Create mcp_server.py**

Create `server/mcp_server.py`:

```python
"""Standalone stdio MCP server for IDE wiki memory integration."""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import suppress
from typing import Any

from fastmcp import Context, FastMCP
from fastmcp.server.lifespan import lifespan

from server.config import get_settings
from server.db.database import init_db
from server.models.api import QueryMode
from server.pipeline.ingest_worker import IngestJob, ingest_worker_loop
from server.services import memory_api
from server.services.memory_api import IngestQueueFullError

logger = logging.getLogger(__name__)


@lifespan
async def app_lifespan(server: FastMCP):
    settings = get_settings()
    await init_db(settings)
    queue: asyncio.Queue[IngestJob] = asyncio.Queue(maxsize=settings.max_queue_size)
    worker_task = asyncio.create_task(ingest_worker_loop(queue, settings))
    logger.info("mem-weaver MCP server started (db=%s)", settings.db_path)
    try:
        yield {"settings": settings, "queue": queue, "worker_task": worker_task}
    finally:
        worker_task.cancel()
        with suppress(asyncio.CancelledError):
            await worker_task
        logger.info("mem-weaver MCP server stopped")


mcp = FastMCP(
    "mem-weaver",
    instructions=(
        "Local wiki memory for this project. "
        "Use wiki_search before answering questions about project knowledge. "
        "Use wiki_ingest to persist useful Q/A after solving problems."
    ),
    lifespan=app_lifespan,
)


def _ctx_state(ctx: Context) -> tuple[Any, asyncio.Queue[IngestJob]]:
    settings = ctx.lifespan_context["settings"]
    queue = ctx.lifespan_context["queue"]
    return settings, queue


def _slim_results(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "title": r.get("title"),
            "path": r.get("path"),
            "snippet": r.get("snippet"),
            "score": r.get("score"),
            "tags": r.get("tags"),
        }
        for r in rows
    ]


def _json_text(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)


@mcp.tool
async def wiki_search(
    query: str,
    limit: int = 5,
    mode: str = "hybrid",
    ctx: Context | None = None,
) -> str:
    """Search compiled wiki pages (hybrid FTS5 + vector by default)."""
    assert ctx is not None
    settings, _ = _ctx_state(ctx)
    try:
        query_mode = QueryMode(mode)
    except ValueError:
        return _json_text({"error": f"invalid mode: {mode}"})

    logger.info("wiki_search query=%r mode=%s limit=%d", query, mode, limit)
    result = await memory_api.search_wiki(
        settings, query, limit=limit, mode=query_mode
    )
    if result.get("error"):
        return _json_text({"error": result["error"], "detail": result.get("detail")})

    return _json_text(
        {
            "query": result["query"],
            "mode": result["mode"],
            "total": result["total"],
            "results": _slim_results(result["results"]),
        }
    )


@mcp.tool
async def wiki_ingest(
    question: str,
    answer: str,
    tags: list[str] | None = None,
    source: str = "mcp",
    ctx: Context | None = None,
) -> str:
    """Save a Q/A pair to the async wiki compile pipeline."""
    assert ctx is not None
    settings, queue = _ctx_state(ctx)
    logger.info("wiki_ingest source=%s tags=%s", source, tags)
    try:
        result = await memory_api.enqueue_ingest(
            settings,
            queue,
            question=question,
            answer=answer,
            source=source,
            tags=tags or [],
        )
    except IngestQueueFullError as err:
        return _json_text(
            {"error": "ingest queue full", "queue_depth": err.queue_depth}
        )
    except ValueError as err:
        return _json_text({"error": str(err)})
    return _json_text(result)


@mcp.tool
async def wiki_get_page(slug: str, ctx: Context | None = None) -> str:
    """Fetch full markdown content for a wiki page by slug."""
    assert ctx is not None
    settings, _ = _ctx_state(ctx)
    logger.info("wiki_get_page slug=%s", slug)
    result = await memory_api.get_wiki_page(settings, slug)
    return _json_text(result)


@mcp.tool
async def wiki_stats(ctx: Context | None = None) -> str:
    """Return wiki vault counters, Ollama reachability, and ingest queue depth."""
    assert ctx is not None
    settings, queue = _ctx_state(ctx)
    result = await memory_api.get_wiki_stats(settings, queue)
    return _json_text(result)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    mcp.run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify module loads**

Run: `./venv/bin/python -c "from server import mcp_server; print([t.name for t in mcp_server.mcp._tool_manager.list_tools()])"`

If internal API differs, run: `./venv/bin/python -m server.mcp_server` in one terminal and confirm no import errors on startup (Ctrl+C to stop).

Alternative smoke: `./venv/bin/python -c "import server.mcp_server; print('ok')"`

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add server/mcp_server.py
git commit -m "feat: add standalone stdio MCP server with four wiki tools"
```

---

### Task 8: MCP in-process smoke tests

**Files:**
- Create: `tests/test_mcp_server.py`

- [ ] **Step 1: Write MCP smoke tests**

Create `tests/test_mcp_server.py`:

```python
"""In-process FastMCP smoke tests (no subprocess)."""

import json
from pathlib import Path

import pytest
from fastmcp import Client

from server.config import Settings
from server.mcp_server import mcp


@pytest.fixture
def mcp_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    base = tmp_path / "mw"
    base.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("DB_PATH", str(base / "wiki.db"))
    monkeypatch.setenv("WIKI_DIR", str(base / "wiki"))
    monkeypatch.setenv("RAW_DIR", str(base / "raw"))
    monkeypatch.setenv("DLQ_DIR", str(base / "failed"))
    monkeypatch.setenv("OLLAMA_HOST", "http://127.0.0.1:9")
    return base


@pytest.mark.asyncio
async def test_mcp_lists_four_tools(mcp_env: Path) -> None:
    async with Client(mcp) as client:
        tools = await client.list_tools()
    names = {t.name for t in tools}
    assert names == {"wiki_search", "wiki_ingest", "wiki_get_page", "wiki_stats"}


@pytest.mark.asyncio
async def test_mcp_wiki_stats_call(mcp_env: Path) -> None:
    async with Client(mcp) as client:
        result = await client.call_tool("wiki_stats", {})
    payload = json.loads(result.content[0].text)
    assert "wiki_pages" in payload
    assert payload["ollama"] in {"reachable", "unreachable"}
```

Adjust `result.content[0].text` if FastMCP Client returns `.data` dict directly — use whichever the installed fastmcp version provides. Prefer:

```python
    data = result.data
    if isinstance(data, str):
        payload = json.loads(data)
    else:
        payload = data
```

- [ ] **Step 2: Run MCP tests**

Run: `./venv/bin/pytest tests/test_mcp_server.py -v`

Expected: PASS (2 tests)

- [ ] **Step 3: Run full test suite**

Run: `./venv/bin/pytest tests/ -v`

Expected: all PASS

- [ ] **Step 4: Commit**

```bash
git add tests/test_mcp_server.py
git commit -m "test: add in-process MCP server smoke tests"
```

---

### Task 9: Documentation and example MCP config

**Files:**
- Create: `.cursor/mcp.json.example`
- Modify: `README.md`

- [ ] **Step 1: Add example MCP config**

Create `.cursor/mcp.json.example`:

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

- [ ] **Step 2: Add README section**

Append to `README.md` after the "Run Locally" section:

```markdown
## MCP Server (IDE integration)

Expose wiki memory to Cursor, Claude Code, or Opencode as MCP tools.

### Prerequisites

1. Ollama running (`ollama serve`) with your model pulled
2. Python venv installed (`pip install -r requirements.txt`)
3. **Do not** run `uvicorn` while using MCP ingest (single ingest worker)

### Setup

1. Copy `.cursor/mcp.json.example` to `.cursor/mcp.json` (or add to your global MCP config)
2. Set `cwd` to this repo's absolute path
3. Restart Cursor

### Tools

| Tool | Purpose |
|------|---------|
| `wiki_search` | Hybrid FTS5 + vector search over compiled wiki |
| `wiki_ingest` | Save Q/A to async wiki compile pipeline |
| `wiki_get_page` | Fetch full markdown by slug |
| `wiki_stats` | Vault counters + Ollama reachability |

### Manual smoke check

Ask the agent: "Search my wiki for FastAPI patterns" — it should call `wiki_search`.
```

- [ ] **Step 3: Commit**

```bash
git add .cursor/mcp.json.example README.md
git commit -m "docs: add MCP server setup instructions and example config"
```

---

### Task 10: Final verification

- [ ] **Step 1: Run full test suite**

Run: `./venv/bin/pytest tests/ -v`

Expected: all PASS

- [ ] **Step 2: Run ruff (if configured)**

Run: `./venv/bin/ruff check server/services/memory_api.py server/mcp_server.py server/main.py tests/test_memory_api.py tests/test_mcp_server.py`

Expected: no errors (fix any reported issues)

- [ ] **Step 3: Manual MCP launch smoke**

Run: `./venv/bin/python -m server.mcp_server`

Expected: process starts, logs "mem-weaver MCP server started", blocks on stdin. Ctrl+C stops cleanly.

---

## Spec Coverage Checklist

| Spec requirement | Task |
|------------------|------|
| Standalone stdio MCP | Task 7 |
| FastMCP library | Task 1 |
| Shared memory_api layer | Tasks 2–5 |
| main.py delegation | Task 6 |
| wiki_search tool | Task 7 |
| wiki_ingest tool | Task 7 |
| wiki_get_page tool | Task 7 |
| wiki_stats tool | Task 7 |
| Self-contained lifespan (DB + worker) | Task 7 |
| Error handling as JSON | Tasks 4, 7 |
| Unit tests memory_api | Tasks 2–5 |
| MCP smoke tests | Task 8 |
| .cursor/mcp.json.example + README | Task 9 |
| No chat/SSE MCP tool | — (intentionally omitted) |
