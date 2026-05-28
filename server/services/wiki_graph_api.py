"""Build the wiki graph from SQLite pages + wiki_links tables."""

from __future__ import annotations

import aiosqlite

from server.config import Settings


async def get_wiki_graph(cfg: Settings) -> dict:
    """Return nodes (pages) and edges (wiki_links) for the graph view."""
    async with aiosqlite.connect(cfg.db_path) as db:
        db.row_factory = aiosqlite.Row

        cur = await db.execute("""
            SELECT id, title, type AS category, inbound_links
            FROM pages
            WHERE id IS NOT NULL
        """)
        nodes = [dict(r) for r in await cur.fetchall()]

        cur = await db.execute("""
            SELECT from_page AS source, to_page AS target
            FROM wiki_links
        """)
        edges = [dict(r) for r in await cur.fetchall()]

    return {"nodes": nodes, "edges": edges}
