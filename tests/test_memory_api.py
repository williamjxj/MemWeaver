"""Unit tests for server.services.memory_api."""

from pathlib import Path

import pytest

from server.config import Settings
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
