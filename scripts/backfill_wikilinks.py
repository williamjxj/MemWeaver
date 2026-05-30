#!/usr/bin/env python3
"""One-shot backfill: extract wikilinks from wiki pages and rebuild graph edges.

Usage:
    python scripts/backfill_wikilinks.py

This reparses every stored wiki page, rewrites ``wiki_links``, and recomputes
``pages.inbound_links`` so the Graph View has real edges to render.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

# Ensure the project root is on sys.path so ``server`` imports resolve.
_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent
sys.path.insert(0, str(_PROJECT_ROOT))

import aiosqlite

from server.config import get_settings
from server.pipeline import wiki_graph

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("backfill_wikilinks")


async def backfill() -> int:
    """Rebuild outbound links for all pages and recompute inbound counts."""
    settings = get_settings()
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(settings.db_path, check_same_thread=False) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT id, content FROM pages ORDER BY id")
        rows = await cur.fetchall()

        if not rows:
            logger.info("No pages found in DB. Nothing to backfill.")
            return 0

        logger.info("Found %d page(s) to scan.", len(rows))

        for index, row in enumerate(rows, start=1):
            page_id = str(row["id"])
            content = str(row["content"] or "")
            await wiki_graph.sync_outbound_links(db, page_id, content)
            logger.info("  ✓ %s (%d/%d)", page_id, index, len(rows))

        await wiki_graph.recompute_inbound_counts(db)
        await db.commit()

    logger.info("Wikilink graph backfill complete.")
    return len(rows)


def main() -> None:
    asyncio.run(backfill())


if __name__ == "__main__":
    main()