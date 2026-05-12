"""Vector (semantic) search over ``page_embeddings`` via sqlite-vec."""

import json
from typing import Any

import aiosqlite
import sqlite_vec

from server.config import Settings
from server.db.vec import load_vec


async def search_semantic(
    settings: Settings,
    query_vec: list[float],
    limit: int,
) -> list[dict[str, Any]]:
    """Return wiki pages ranked by cosine distance against ``query_vec``.

    Args:
        settings: App settings (provides db_path).
        query_vec: Float vector from :func:`embedder.embed_text`.
        limit: Maximum results to return.

    Returns:
        List of dicts with keys ``id``, ``title``, ``type``, ``path``,
        ``tags``, ``updated``, ``inbound_links``, ``score`` (cosine distance),
        ``snippet`` (empty for vec-only results).
    """
    serialized = sqlite_vec.serialize_float32(query_vec)

    async with aiosqlite.connect(settings.db_path, check_same_thread=False) as db:
        await load_vec(db)
        db.row_factory = aiosqlite.Row

        cur = await db.execute(
            """
            SELECT pe.page_id,
                   pe.distance,
                   p.title,
                   p.type,
                   p.path,
                   p.tags,
                   p.updated_at AS updated,
                   p.inbound_links
            FROM (
                SELECT page_id, distance
                FROM page_embeddings
                WHERE embedding MATCH ?
                ORDER BY distance
                LIMIT ?
            ) pe
            JOIN pages p ON p.id = pe.page_id
            """,
            [serialized, limit],
        )
        rows = await cur.fetchall()

    out: list[dict[str, Any]] = []
    for r in rows:
        tags_raw = r["tags"] or "[]"
        try:
            tags = json.loads(tags_raw)
        except json.JSONDecodeError:
            tags = []

        out.append(
            {
                "id": r["page_id"],
                "title": r["title"],
                "type": r["type"],
                "path": r["path"],
                "snippet": "",
                "tags": tags,
                "score": float(r["distance"]),  # cosine distance (0 = identical)
                "updated": r["updated"],
                "inbound_links": int(r["inbound_links"] or 0),
            }
        )

    return out
