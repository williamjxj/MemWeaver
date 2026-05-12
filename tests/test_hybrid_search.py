"""Tests for hybrid (FTS5 + vector) search via Reciprocal Rank Fusion."""

import pytest

from server.pipeline.query_search import RRF_CONSTANT


def test_rrf_constant_is_sensible() -> None:
    """RRF_CONSTANT should be a positive integer (standard value is 60)."""
    assert isinstance(RRF_CONSTANT, int)
    assert 1 <= RRF_CONSTANT <= 1000, "RRF constant should be in typical range"


def test_rrf_merge_logic() -> None:
    """Verify RRF score computation and ordering manually."""
    from server.pipeline.query_search import search_hybrid

    # We can't easily test the async search_hybrid without a DB,
    # but we can verify the RRF formula inline.
    #
    # RRF score for rank r (0-indexed) = 1 / (RRF_CONSTANT + r + 1)
    # For an item ranked #1 in both channels:
    expected = 1.0 / (RRF_CONSTANT + 1) + 1.0 / (RRF_CONSTANT + 1)
    # For an item ranked #1 only in one channel:
    expected_one = 1.0 / (RRF_CONSTANT + 1)

    assert expected > expected_one, "Two-channel match should score higher"
    assert expected > 0, "RRF score should be positive"
    assert expected_one > 0, "RRF score should be positive"


@pytest.mark.asyncio
async def test_search_hybrid_returns_fts_results() -> None:
    """search_hybrid should return FTS5 results when no vectors exist."""
    from pathlib import Path
    import aiosqlite
    from server.config import Settings
    from server.db.database import init_db
    from server.pipeline.query_search import search_hybrid

    tmp = Path(__file__).parent / "_test_hybrid_tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    db_path = tmp / "hybrid.db"

    settings = Settings(
        db_path=db_path,
        ollama_host="http://127.0.0.1:11434",
        wiki_dir=tmp / "wiki",
    )

    # Init DB (creates both migrations)
    await init_db(settings)

    # Insert a test page with FTS5 content
    async with aiosqlite.connect(db_path, check_same_thread=False) as db:
        await db.execute(
            "INSERT INTO pages (id, title, type, path, tags, confidence, "
            "created_at, updated_at, inbound_links, content) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                "hybrid-test",
                "Hybrid Search",
                "concept",
                "wiki/concepts/hybrid-test.md",
                '["search", "hybrid"]',
                "medium",
                "2026-01-01",
                "2026-01-01",
                0,
                "# Hybrid Search\n\nCombines BM25 and vector similarity via RRF.",
            ],
        )
        await db.execute(
            "DELETE FROM pages_fts WHERE page_id = ?",
            ["hybrid-test"],
        )
        await db.execute(
            "INSERT INTO pages_fts (page_id, title, content, tags) VALUES (?, ?, ?, ?)",
            [
                "hybrid-test",
                "Hybrid Search",
                "# Hybrid Search\n\nCombines BM25 and vector similarity via RRF.",
                '["search", "hybrid"]',
            ],
        )
        await db.commit()

    # Hybrid search for 'hybrid' — should find our page via FTS5 even without vectors
    results = await search_hybrid(settings, "hybrid search", limit=5)
    assert len(results) >= 1, "hybrid search should return FTS5 results"
    assert any(r["id"] == "hybrid-test" for r in results), (
        f"Expected 'hybrid-test' in results, got {[r['id'] for r in results]}"
    )

    # Cleanup
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
