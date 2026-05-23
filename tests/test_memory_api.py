"""Unit tests for server.services.memory_api."""

import asyncio
from pathlib import Path

import pytest

from server.config import Settings
from server.db.database import init_db
from server.models.api import QueryMode
from server.pipeline.ingest_worker import IngestJob
from server.services import memory_api


@pytest.fixture
def isolated_settings(tmp_path: Path) -> Settings:
    base = tmp_path / "mw"
    base.mkdir(parents=True, exist_ok=True)
    wiki = base / "wiki"
    wiki.mkdir(parents=True, exist_ok=True)
    return Settings(
        db_path=base / "t.db",
        wiki_dir=wiki,
        raw_dir=base / "raw",
        dlq_dir=base / "failed",
        ollama_host="http://127.0.0.1:9",
        ollama_model="test-model",
        ollama_timeout=5.0,
    )


@pytest.mark.asyncio
async def test_get_wiki_page_found(isolated_settings: Settings) -> None:
    slug = "concepts/hybrid-search"
    path = isolated_settings.wiki_dir / f"{slug}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# Hybrid Search\n", encoding="utf-8")

    result = await memory_api.get_wiki_page(isolated_settings, slug)

    assert result["slug"] == slug
    assert "Hybrid Search" in result["content"]


@pytest.mark.asyncio
async def test_get_wiki_page_missing(isolated_settings: Settings) -> None:
    result = await memory_api.get_wiki_page(isolated_settings, "concepts/missing")

    assert result["slug"] == "concepts/missing"
    assert result["content"] == ""


@pytest.fixture
def db_settings(tmp_path: Path) -> Settings:
    base = tmp_path / "mw"
    base.mkdir(parents=True, exist_ok=True)
    s = Settings(
        db_path=base / "t.db",
        wiki_dir=base / "wiki",
        raw_dir=base / "raw",
        dlq_dir=base / "failed",
        ollama_host="http://127.0.0.1:9",
        ollama_model="test-model",
        ollama_timeout=5.0,
    )
    asyncio.run(init_db(s))
    return s


async def _seed_page(settings: Settings, page_id: str, title: str, content: str) -> None:
    import aiosqlite

    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute(
            """
            INSERT INTO pages (id, title, type, path, tags, confidence,
                               created_at, updated_at, inbound_links, content)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                page_id,
                title,
                "concept",
                f"wiki/concepts/{page_id}.md",
                '["search"]',
                "medium",
                "2026-01-01",
                "2026-01-01",
                0,
                content,
            ],
        )
        await db.execute("DELETE FROM pages_fts WHERE page_id = ?", [page_id])
        await db.execute(
            "INSERT INTO pages_fts (page_id, title, content, tags) VALUES (?, ?, ?, ?)",
            [page_id, title, content, "search"],
        )
        await db.commit()


@pytest.mark.asyncio
async def test_search_wiki_empty_query(db_settings: Settings) -> None:
    result = await memory_api.search_wiki(db_settings, "   ")

    assert "error" in result
    assert "empty" in result["error"].lower()


@pytest.mark.asyncio
async def test_search_wiki_keyword(db_settings: Settings) -> None:
    await _seed_page(
        db_settings,
        "fastapi-patterns",
        "FastAPI Patterns",
        "Use dependency injection in FastAPI routes.",
    )

    result = await memory_api.search_wiki(
        db_settings,
        "FastAPI",
        limit=5,
        mode=QueryMode.KEYWORD,
    )

    assert result["error"] is None
    assert result["total"] >= 1
    assert any("fastapi" in (r.get("title") or "").lower() for r in result["results"])


@pytest.mark.asyncio
async def test_enqueue_ingest_accepted(isolated_settings: Settings) -> None:
    queue: asyncio.Queue[IngestJob] = asyncio.Queue(maxsize=10)

    result = await memory_api.enqueue_ingest(
        isolated_settings,
        queue,
        question="What is MCP?",
        answer="Model Context Protocol exposes tools to LLMs.",
        source="test",
        tags=["mcp"],
    )

    assert result["status"] == "accepted"
    assert result["ingest_id"].startswith("ing_")
    assert queue.qsize() == 1
    job = queue.get_nowait()
    assert job.question == "What is MCP?"


@pytest.mark.asyncio
async def test_enqueue_ingest_queue_full(isolated_settings: Settings) -> None:
    # asyncio.Queue(maxsize=0) is unbounded; use maxsize=1 and fill it.
    queue: asyncio.Queue[IngestJob] = asyncio.Queue(maxsize=1)
    await memory_api.enqueue_ingest(
        isolated_settings,
        queue,
        question="First",
        answer="Answer one",
    )
    assert queue.qsize() == 1

    with pytest.raises(memory_api.IngestQueueFullError) as exc:
        await memory_api.enqueue_ingest(
            isolated_settings,
            queue,
            question="Q",
            answer="A",
        )

    assert exc.value.queue_depth == 1
