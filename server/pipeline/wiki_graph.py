"""Wikilink extraction and `wiki_links` / inbound link counts."""

from __future__ import annotations

import re

import aiosqlite

from server.pipeline.textutil import slugify

_WIKILINK = re.compile(r"\[\[([^\]|#]+)(?:\|[^\]]+)?\]\]")


def extract_wikilink_targets(markdown: str) -> list[str]:
    """Return target page ids from Obsidian-style `[[target]]` / `[[target|alias]]`."""
    seen: list[str] = []
    for m in _WIKILINK.finditer(markdown or ""):
        raw = m.group(1).strip()
        if not raw:
            continue
        tid = slugify(raw)
        if tid and tid not in seen:
            seen.append(tid)
    return seen


async def sync_outbound_links(
    db: aiosqlite.Connection,
    from_page_id: str,
    markdown: str,
) -> None:
    """Replace outbound edges from `from_page_id`; only edges to existing `pages.id`."""
    await db.execute("DELETE FROM wiki_links WHERE from_page = ?", (from_page_id,))
    for tid in extract_wikilink_targets(markdown):
        if tid == from_page_id:
            continue
        cur = await db.execute("SELECT 1 FROM pages WHERE id = ? LIMIT 1", (tid,))
        if await cur.fetchone():
            await db.execute(
                "INSERT OR IGNORE INTO wiki_links(from_page, to_page) VALUES (?, ?)",
                (from_page_id, tid),
            )


async def recompute_inbound_counts(db: aiosqlite.Connection) -> None:
    """Set `pages.inbound_links` from indegree in `wiki_links`."""
    await db.execute(
        """
        UPDATE pages SET inbound_links = (
            SELECT COUNT(*) FROM wiki_links w WHERE w.to_page = pages.id
        )
        """
    )
