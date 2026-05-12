"""Tests for the Ollama embedding helper (server/pipeline/embedder.py)."""

from pathlib import Path

import pytest

from server.config import Settings
from server.pipeline.embedder import embed_text, embed_page, EMBEDDING_DIMS


@pytest.mark.asyncio
async def test_embed_text_returns_correct_dims() -> None:
    """embed_text should return a float vector with EMBEDDING_DIMS elements."""
    s = Settings(ollama_host="http://127.0.0.1:11434")
    vec = await embed_text(s, "Hello from mem-weaver test")
    assert isinstance(vec, list)
    assert len(vec) == EMBEDDING_DIMS
    assert all(isinstance(v, float) for v in vec)
    # Basic sanity: a meaningful vector should have non-zero values
    assert any(v != 0.0 for v in vec)


@pytest.mark.asyncio
async def test_embed_text_similar_texts_have_similar_vectors() -> None:
    """Two semantically similar texts should produce closer vectors than dissimilar ones."""
    s = Settings(ollama_host="http://127.0.0.1:11434")

    a = await embed_text(s, "Python is a programming language")
    b = await embed_text(s, "Python is used for software development")
    c = await embed_text(s, "The Eiffel Tower is in Paris")

    import math

    def cosine_dist(v1: list[float], v2: list[float]) -> float:
        dot = sum(x * y for x, y in zip(v1, v2))
        n1 = math.sqrt(sum(x * x for x in v1))
        n2 = math.sqrt(sum(y * y for y in v2))
        return 1.0 - dot / (n1 * n2 + 1e-10)

    dist_ab = cosine_dist(a, b)
    dist_ac = cosine_dist(a, c)

    # Python-related texts should be more similar than Python vs. Paris
    assert dist_ab < dist_ac, (
        f"Expected dist(Python, Python-variant) < dist(Python, Paris): "
        f"{dist_ab:.4f} vs {dist_ac:.4f}"
    )


@pytest.mark.asyncio
async def test_embed_page_upserts_vector(tmp_path: Path) -> None:
    """embed_page should write a vector into page_embeddings without error."""
    db_path = tmp_path / "test_embed.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    import aiosqlite
    from server.db.vec import load_vec

    # Set up a minimal page + vec0 table
    async with aiosqlite.connect(db_path, check_same_thread=False) as db:
        await load_vec(db)
        await db.execute(
            "CREATE TABLE IF NOT EXISTS pages (id TEXT PRIMARY KEY, content TEXT)"
        )
        await db.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS page_embeddings "
            "USING vec0(page_id TEXT PRIMARY KEY, embedding float[768])"
        )
        await db.execute(
            "INSERT INTO pages (id, content) VALUES (?, ?)",
            ["test-page", "# Test\n\nHello world."],
        )
        await db.commit()

    s = Settings(db_path=db_path, ollama_host="http://127.0.0.1:11434")
    await embed_page(s, "test-page", "# Test\n\nHello world.")

    # Verify the embedding was stored
    async with aiosqlite.connect(db_path, check_same_thread=False) as db:
        await load_vec(db)
        cur = await db.execute(
            "SELECT COUNT(*) FROM page_embeddings WHERE page_id = ?",
            ["test-page"],
        )
        count = (await cur.fetchone())[0]
    assert count == 1, "embedding should be present after embed_page"
