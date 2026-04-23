"""FastAPI delegator: ingest (async pipeline), FTS query, health, stats."""

import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timezone
from uuid import uuid4

import aiosqlite
import httpx
from fastapi import FastAPI, HTTPException, Query

from server.config import get_settings
from server.db.database import init_db
from server.models.api import (
    HealthResponse,
    IngestPayload,
    IngestResponse,
    QueryResponse,
    StatsResponse,
)
from server.pipeline.ingest_worker import IngestJob, ingest_worker_loop
from server.pipeline.query_search import search_pages, synthesize_answer

logger = logging.getLogger(__name__)


def _make_ingest_id() -> str:
    return f"ing_{datetime.now(timezone.utc).strftime('%Y%m%d')}_{uuid4().hex[:8]}"


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    await init_db(settings)
    app.state.settings = settings
    app.state.ingest_queue = asyncio.Queue(maxsize=settings.max_queue_size)
    app.state.worker_task = asyncio.create_task(
        ingest_worker_loop(app.state.ingest_queue, settings)
    )
    yield
    app.state.worker_task.cancel()
    with suppress(asyncio.CancelledError):
        await app.state.worker_task


settings = get_settings()
app = FastAPI(title=settings.app_name, lifespan=lifespan)


@app.post("/ingest", response_model=IngestResponse, status_code=202)
async def ingest(payload: IngestPayload) -> IngestResponse:
    """Accept Q/A, return 202; Ollama + wiki + DB run on a background worker."""
    cfg = app.state.settings
    ingest_id = _make_ingest_id()
    received = payload.timestamp or datetime.now(timezone.utc)
    if received.tzinfo is None:
        received = received.replace(tzinfo=timezone.utc)
    job = IngestJob(
        ingest_id=ingest_id,
        question=payload.question.strip(),
        answer=payload.answer.strip(),
        source=payload.source or "unknown",
        session_id=payload.session_id,
        tags=payload.tags,
        received_at=received,
    )
    try:
        app.state.ingest_queue.put_nowait(job)
    except asyncio.QueueFull:
        raise HTTPException(status_code=503, detail="ingest queue is full") from None
    return IngestResponse(
        status="accepted",
        ingest_id=ingest_id,
        queued_at=datetime.now(timezone.utc),
    )


@app.get("/query", response_model=QueryResponse)
async def query(
    q: str = Query(..., description="Search query"),
    limit: int = Query(5, ge=1, le=50),
    summarize: bool = Query(
        False,
        description="If true, run Ollama over top wiki snippets (uses extra tokens).",
    ),
) -> QueryResponse:
    cfg = app.state.settings
    rows = await search_pages(cfg, q, limit)
    summarized: str | None = None
    if summarize and rows:
        snippets = [str(r.get("snippet") or "") for r in rows]
        try:
            summarized = await synthesize_answer(cfg, q, snippets)
        except Exception:
            logger.exception("query summarization failed")
            summarized = None
    return QueryResponse(query=q, results=rows, total=len(rows), summarized_answer=summarized)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    cfg = app.state.settings
    ollama_status = "reachable"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{cfg.ollama_host.rstrip('/')}/api/tags")
            r.raise_for_status()
    except Exception:
        ollama_status = "unreachable"

    db_status = "ok"
    n_pages = 0
    n_qa = 0
    try:
        async with aiosqlite.connect(cfg.db_path) as db:
            cur = await db.execute("SELECT COUNT(*) FROM pages")
            row = await cur.fetchone()
            n_pages = int(row[0]) if row else 0
            cur = await db.execute("SELECT COUNT(*) FROM qa_pairs")
            row = await cur.fetchone()
            n_qa = int(row[0]) if row else 0
    except Exception:
        db_status = "error"

    depth = app.state.ingest_queue.qsize()
    return HealthResponse(
        status="ok",
        ollama=ollama_status,
        db=db_status,
        queue_depth=depth,
        wiki_pages=n_pages,
        qa_pairs=n_qa,
    )


@app.get("/stats", response_model=StatsResponse)
async def stats() -> StatsResponse:
    cfg = app.state.settings
    async with aiosqlite.connect(cfg.db_path) as db:
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
    return StatsResponse(
        total_ingests=total_ingests,
        total_wiki_pages=total_wiki_pages,
        top_tags=top_tags,
        last_ingest=last_ingest,
        orphan_pages=orphan_pages,
    )
