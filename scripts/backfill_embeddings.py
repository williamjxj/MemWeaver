#!/usr/bin/env python3
"""One-shot backfill: embed all existing wiki pages for semantic search.

Usage:
    python scripts/backfill_embeddings.py

Requires:
    - Ollama running with nomic-embed-text model pulled
    - Wiki DB at the path configured in .env or default db/wiki.db
"""

import asyncio
import logging
import sys
from pathlib import Path

# Ensure the project root is on sys.path so ``server`` imports resolve
_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent
sys.path.insert(0, str(_PROJECT_ROOT))

import aiosqlite

from server.config import get_settings
from server.db.vec import load_vec
from server.pipeline.embedder import embed_text, EMBEDDING_DIMS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("backfill_embeddings")


async def backfill() -> int:
    """Read every row in ``pages``, embed, upsert into ``page_embeddings``.

    Returns the number of pages processed.
    """
    settings = get_settings()
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)

    # Read all page IDs and content
    async with aiosqlite.connect(settings.db_path, check_same_thread=False) as db:
        # Ensure the vec extension and vec0 table exist
        await load_vec(db)
        await db.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS page_embeddings USING vec0("
            "  page_id TEXT PRIMARY KEY,"
            "  embedding float[768]"
            ")"
        )

        cur = await db.execute(
            "SELECT id, content FROM pages ORDER BY id"
        )
        rows = await cur.fetchall()

    if not rows:
        logger.info("No pages found in DB. Nothing to backfill.")
        return 0

    logger.info("Found %d page(s) to embed. Starting…", len(rows))

    # Use embed_pages_batch equivalent: process sequentially
    async with aiosqlite.connect(settings.db_path, check_same_thread=False) as db:
        await load_vec(db)

        ok_count = 0
        fail_count = 0

        for page_id, content in rows:
            try:
                logger.debug("Embedding page %s …", page_id)
                # Strip frontmatter for vector quality
                text = content
                if text.startswith("---"):
                    end = text.find("\n---\n", 3)
                    if end >= 0:
                        text = text[end + 5 :].lstrip()

                vec = await embed_text(settings, text)
                if len(vec) != EMBEDDING_DIMS:
                    logger.warning(
                        "Page %s returned %d dims (expected %d); padding",
                        page_id, len(vec), EMBEDDING_DIMS,
                    )
                    # Pad or truncate to expected dimensions
                    vec = (vec + [0.0] * EMBEDDING_DIMS)[:EMBEDDING_DIMS]

                import sqlite_vec
                serialized = sqlite_vec.serialize_float32(vec)

                await db.execute(
                    "DELETE FROM page_embeddings WHERE page_id = ?",
                    [page_id],
                )
                await db.execute(
                    "INSERT INTO page_embeddings (page_id, embedding) VALUES (?, ?)",
                    [page_id, serialized],
                )
                ok_count += 1
                logger.info("  ✓ %s  (%d/%d)", page_id, ok_count + fail_count, len(rows))
            except Exception:
                logger.exception("  ✗ %s  failed", page_id)
                fail_count += 1

        await db.commit()

    logger.info(
        "Backfill complete: %d succeeded, %d failed out of %d",
        ok_count, fail_count, len(rows),
    )
    return ok_count


def main() -> None:
    count = asyncio.run(backfill())
    if count:
        logger.info("Semantic search is now available for %d page(s).", count)


if __name__ == "__main__":
    main()
