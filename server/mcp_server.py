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
    *,
    ctx: Context,
) -> str:
    """Search compiled wiki pages (hybrid FTS5 + vector by default)."""
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
    *,
    ctx: Context,
) -> str:
    """Save a Q/A pair to the async wiki compile pipeline."""
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
async def wiki_get_page(slug: str, *, ctx: Context) -> str:
    """Fetch full markdown content for a wiki page by slug."""
    settings, _ = _ctx_state(ctx)
    logger.info("wiki_get_page slug=%s", slug)
    result = await memory_api.get_wiki_page(settings, slug)
    return _json_text(result)


@mcp.tool
async def wiki_stats(*, ctx: Context) -> str:
    """Return wiki vault counters, Ollama reachability, and ingest queue depth."""
    settings, queue = _ctx_state(ctx)
    result = await memory_api.get_wiki_stats(settings, queue)
    return _json_text(result)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    mcp.run()


if __name__ == "__main__":
    main()
