"""Shared wiki memory operations for HTTP routes and MCP tools."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import aiosqlite
import httpx

from server.config import Settings
from server.models.api import QueryMode
from server.pipeline.embedder import embed_text
from server.pipeline.ingest_worker import IngestJob
from server.pipeline.query_search import search_hybrid, search_pages
from server.pipeline.search_semantic import search_semantic

logger = logging.getLogger(__name__)

MCP_SEARCH_LIMIT_MAX = 20


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


async def get_wiki_page(settings: Settings, slug: str) -> dict[str, str]:
    """Read wiki markdown by slug. Returns empty content if not found."""
    article_path = Path(settings.wiki_dir) / f"{slug}.md"
    if article_path.exists():
        content = article_path.read_text(encoding="utf-8")
    else:
        content = ""
    return {"slug": slug, "content": content}


async def search_wiki(
    settings: Settings,
    query: str,
    *,
    limit: int = 5,
    mode: QueryMode = QueryMode.HYBRID,
) -> dict[str, Any]:
    """Search wiki pages. Returns result dict or ``{"error": ...}`` on validation failure."""
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

    return {
        "error": None,
        "query": q,
        "mode": mode.value,
        "total": len(rows),
        "results": rows,
    }


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
