"""FTS-backed wiki search + hybrid (FTS + vector) via Reciprocal Rank Fusion."""

import asyncio
import json
from typing import Any

import aiosqlite

from server.config import Settings
from server.db.database import fts_match_terms
from server.ollama.client import ollama_generate_text
from server.pipeline.embedder import embed_text
from server.pipeline.search_semantic import search_semantic

RRF_CONSTANT = 60  # standard RRF rank offset


async def search_pages(settings: Settings, q: str, limit: int) -> list[dict[str, Any]]:
    """Return ranked page hits (BM25 on `pages_fts`)."""
    match = fts_match_terms(q)
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """
            SELECT p.id, p.title, p.type, p.path, p.tags, p.updated_at AS updated,
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
                "id": r["id"],
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


async def search_hybrid(
    settings: Settings,
    q: str,
    limit: int,
) -> list[dict[str, Any]]:
    """Hybrid search: FTS5 BM25 + vector cosine similarity, merged via RRF.

    Runs both searches in parallel, merges via Reciprocal Rank Fusion,
    and returns the top ``limit`` results.
    """
    query_vec = await embed_text(settings, q)

    # Fetch extra candidates from each channel for richer merge
    fts_limit = limit * 3
    vec_limit = limit * 3

    fts_task = search_pages(settings, q, fts_limit)
    vec_task = search_semantic(settings, query_vec, vec_limit)

    fts_results, vec_results = await asyncio.gather(fts_task, vec_task)

    # RRF merge keyed on page id
    merged: dict[str, dict[str, Any]] = {}

    for rank, r in enumerate(fts_results):
        pid = r["id"]
        merged[pid] = {
            "data": r,
            "rrf_score": 1.0 / (RRF_CONSTANT + rank + 1),
        }

    for rank, r in enumerate(vec_results):
        pid = r["id"]
        if pid in merged:
            merged[pid]["rrf_score"] += 1.0 / (RRF_CONSTANT + rank + 1)
        else:
            merged[pid] = {
                "data": r,
                "rrf_score": 1.0 / (RRF_CONSTANT + rank + 1),
            }

    sorted_results = sorted(
        merged.values(), key=lambda x: x["rrf_score"], reverse=True
    )
    return [r["data"] for r in sorted_results[:limit]]


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
        api_key=settings.ollama_api_key,
    )
