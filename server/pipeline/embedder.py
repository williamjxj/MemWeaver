"""Ollama embedding helper for semantic search."""

import logging
from typing import Sequence

import aiosqlite
import httpx
import sqlite_vec

from server.config import Settings
from server.db.vec import load_vec

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "nomic-embed-text"
EMBEDDING_DIMS = 768


async def embed_text(settings: Settings, text: str) -> list[float]:
    """Call Ollama `/api/embeddings` and return a float vector.

    Args:
        settings: App settings (provides ollama_host).
        text: Input text to embed (truncated to 8192 chars internally
              by nomic-embed-text).

    Returns:
        A list of ``EMBEDDING_DIMS`` floats.

    Raises:
        httpx.HTTPStatusError: If Ollama returns a non-2xx status.
        httpx.TimeoutException: On request timeout.
    """
    url = f"{settings.ollama_host.rstrip('/')}/api/embeddings"
    body = {"model": EMBEDDING_MODEL, "prompt": text}

    async with httpx.AsyncClient(timeout=settings.ollama_timeout) as client:
        r = await client.post(url, json=body)
        r.raise_for_status()
        data = r.json()
        embedding: list[float] = data.get("embedding", [])
        if len(embedding) != EMBEDDING_DIMS:
            logger.warning(
                "expected %d dims, got %d from model %s",
                EMBEDDING_DIMS,
                len(embedding),
                EMBEDDING_MODEL,
            )
        return embedding


async def embed_page(
    settings: Settings,
    page_id: str,
    content: str,
) -> None:
    """Embed a wiki page and upsert its vector into ``page_embeddings``.

    This is called from the ingest pipeline (async background worker) so
    the ~200 ms embedding latency does not affect user-facing responses.

    Args:
        settings: App settings.
        page_id: The ``pages.id`` slug (e.g. ``"attention-mechanism"``).
        content: The full page content — frontmatter + body. The embedder
                 will use ``strip_frontmatter`` internally for better vector quality.
    """
    embed_input = _strip_frontmatter(content) if content.startswith("---") else content
    vector = await embed_text(settings, embed_input)
    serialized = sqlite_vec.serialize_float32(vector)

    async with aiosqlite.connect(settings.db_path, check_same_thread=False) as db:
        await load_vec(db)
        await db.execute(
            "DELETE FROM page_embeddings WHERE page_id = ?",
            [page_id],
        )
        await db.execute(
            "INSERT INTO page_embeddings (page_id, embedding) VALUES (?, ?)",
            [page_id, serialized],
        )
        await db.commit()


async def embed_pages_batch(
    settings: Settings,
    pages: Sequence[tuple[str, str]],
) -> None:
    """Embed multiple pages and batch-upsert into ``page_embeddings``.

    Used by the backfill script. Each page is embedded sequentially to avoid
    overloading Ollama; the embedder itself is I/O-bound (HTTP call) so the
    overall throughput is ~3-5 pages/second.

    Args:
        settings: App settings.
        pages: Sequence of ``(page_id, content)`` tuples.
    """
    async with aiosqlite.connect(settings.db_path, check_same_thread=False) as db:
        await load_vec(db)

        for page_id, content in pages:
            embed_input = _strip_frontmatter(content) if content.startswith("---") else content
            vector = await embed_text(settings, embed_input)
            serialized = sqlite_vec.serialize_float32(vector)
            await db.execute(
                "DELETE FROM page_embeddings WHERE page_id = ?",
                [page_id],
            )
            await db.execute(
                "INSERT INTO page_embeddings (page_id, embedding) VALUES (?, ?)",
                [page_id, serialized],
            )

        await db.commit()


def _strip_frontmatter(md: str) -> str:
    """Remove YAML frontmatter for cleaner embedding input."""
    if not md.startswith("---"):
        return md
    end = md.find("\n---\n", 3)
    if end == -1:
        return md
    return md[end + 5 :].lstrip()
