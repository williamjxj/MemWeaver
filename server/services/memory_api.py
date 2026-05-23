"""Shared wiki memory operations for HTTP routes and MCP tools."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

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
