"""FTS-backed wiki search."""

import json
from typing import Any

import aiosqlite

from server.config import Settings
from server.db.database import fts_match_terms
from server.ollama.client import ollama_generate_text


async def search_pages(settings: Settings, q: str, limit: int) -> list[dict[str, Any]]:
    """Return ranked page hits (BM25 on `pages_fts`)."""
    match = fts_match_terms(q)
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """
            SELECT p.title, p.type, p.path, p.tags, p.updated_at AS updated,
                   p.inbound_links,
                   snippet(pages_fts, 2, '<b>', '</b>', '...', 28) AS snippet,
                   bm25(pages_fts) AS score
            FROM pages_fts
            JOIN pages p ON p.id = pages_fts.page_id
            WHERE pages_fts MATCH ?
            ORDER BY bm25(pages_fts) ASC
            LIMIT ?
            """,
            (match, limit),
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
                "title": r["title"],
                "type": r["type"],
                "path": r["path"],
                "snippet": r["snippet"],
                "tags": tags,
                "score": float(r["score"]),
                "updated": r["updated"],
                "inbound_links": int(r["inbound_links"] or 0),
            }
        )
    return out


async def synthesize_answer(
    settings: Settings,
    query: str,
    snippets: list[str],
) -> str:
    """Optional LLM synthesis over top snippets (query-time, s2 §3.2)."""
    ctx = "\n\n".join(f"---\n{s}" for s in snippets[:5])
    prompt = (
        "You answer using only the provided wiki snippets. Be concise (3-6 sentences). "
        "If snippets are insufficient, say what is missing.\n\n"
        f"Question: {query}\n\nSnippets:\n{ctx}"
    )
    return await ollama_generate_text(
        settings.ollama_host,
        settings.ollama_model,
        prompt,
        timeout=settings.ollama_timeout,
    )
