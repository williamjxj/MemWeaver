"""Tests for semantic (vector) search via sqlite-vec (server/pipeline/search_semantic.py)."""

from pathlib import Path

import pytest

from server.config import Settings
from server.pipeline.search_semantic import search_semantic


@pytest.mark.asyncio
async def test_search_semantic_orders_by_cosine_distance(tmp_path: Path) -> None:
    """With known vectors, the nearest neighbour should be ranked first."""
    import aiosqlite
    import sqlite_vec
    from server.db.vec import load_vec

    db_path = tmp_path / "test_vec_search.db"

    # Seed three vectors in a 4-d space for easy human verification.
    # Each is a 768-d vector; we'll pad the rest with zeros.
    def make_vec(first_four: list[float]) -> bytes:
        """Build a 768-d float32 vector, fill first 4 values, rest zero."""
        v = first_four + [0.0] * (768 - 4)
        return sqlite_vec.serialize_float32(v)

    async with aiosqlite.connect(db_path, check_same_thread=False) as db:
        await load_vec(db)
        await db.execute(
            "CREATE TABLE IF NOT EXISTS pages (id TEXT PRIMARY KEY, title TEXT, "
            "type TEXT, path TEXT, tags TEXT, updated_at TEXT, inbound_links INTEGER, content TEXT)"
        )
        await db.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS page_embeddings "
            "USING vec0(page_id TEXT PRIMARY KEY, embedding float[768])"
        )
        # Insert pages
        for pid, title in [("doc-a", "Document A"), ("doc-b", "Document B"), ("doc-c", "Document C")]:
            await db.execute(
                "INSERT OR IGNORE INTO pages (id, title, type, path, tags, updated_at, "
                "inbound_links, content) VALUES (?, ?, 'concept', ?, '[]', '2026-01-01', 0, ?)",
                [pid, title, f"wiki/concepts/{pid}.md", f"# {title}"],
            )
        # Insert vectors:
        # doc-a: [1, 0, 0, 0, ...]
        # doc-b: [0, 1, 0, 0, ...]
        # doc-c: [0, 0, 1, 0, ...]
        await db.execute("DELETE FROM page_embeddings WHERE page_id IN ('doc-a','doc-b','doc-c')")
        for pid, first4 in [("doc-a", [1.0, 0.0, 0.0, 0.0]),
                             ("doc-b", [0.0, 1.0, 0.0, 0.0]),
                             ("doc-c", [0.0, 0.0, 1.0, 0.0])]:
            await db.execute(
                "INSERT INTO page_embeddings (page_id, embedding) VALUES (?, ?)",
                [pid, make_vec(first4)],
            )
        await db.commit()

    s = Settings(db_path=db_path)

    # Query: near [1, 0, 0, 0, ...] → doc-a should be closest
    query_near_a = [0.95, 0.05, 0.0, 0.0] + [0.0] * (768 - 4)
    results = await search_semantic(s, query_near_a, limit=3)
    assert len(results) >= 1
    assert results[0]["id"] == "doc-a", (
        f"Expected doc-a first for near-[1,0,0,...], got {results[0]['id']}"
    )
    assert results[0]["score"] < results[1]["score"], (
        "nearest neighbour should have smallest distance"
    )

    # Query: near [0, 0, 1, 0, ...] → doc-c should be closest
    query_near_c = [0.0, 0.0, 0.95, 0.0] + [0.0] * (768 - 4)
    results_c = await search_semantic(s, query_near_c, limit=3)
    assert results_c[0]["id"] == "doc-c", (
        f"Expected doc-c first for near-[0,0,1,...], got {results_c[0]['id']}"
    )


@pytest.mark.asyncio
async def test_search_semantic_empty_db_returns_no_results(tmp_path: Path) -> None:
    """Searching an empty vec0 table should return an empty list."""
    import aiosqlite
    from server.db.vec import load_vec

    db_path = tmp_path / "empty.db"

    async with aiosqlite.connect(db_path, check_same_thread=False) as db:
        await load_vec(db)
        await db.execute(
            "CREATE TABLE IF NOT EXISTS pages (id TEXT PRIMARY KEY, title TEXT, "
            "type TEXT, path TEXT, tags TEXT, updated_at TEXT, inbound_links INTEGER, content TEXT)"
        )
        await db.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS page_embeddings "
            "USING vec0(page_id TEXT PRIMARY KEY, embedding float[768])"
        )
        await db.commit()

    s = Settings(db_path=db_path)
    query = [0.0] * 768
    results = await search_semantic(s, query, limit=5)
    assert results == [], "empty DB should return no results"
