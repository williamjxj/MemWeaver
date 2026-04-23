"""Tests for contradiction guard (skips LLM when no existing body)."""

from pathlib import Path

import pytest

from server.config import Settings
from server.pipeline.contradictions import maybe_prepend_contradiction_block


@pytest.mark.asyncio
async def test_maybe_prepend_skips_when_empty_existing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[int] = []

    async def fake_json(*args: object, **kwargs: object) -> dict[str, object]:
        calls.append(1)
        return {"contradicts": True, "note": "x"}

    monkeypatch.setattr(
        "server.pipeline.contradictions.ollama_generate_json",
        fake_json,
    )
    settings = Settings(
        db_path=tmp_path / "db.sqlite",
        wiki_dir=tmp_path / "wiki",
        raw_dir=tmp_path / "raw",
    )
    out = await maybe_prepend_contradiction_block(settings, "", "atom", [], "BODY")
    assert out == "BODY"
    assert calls == []
