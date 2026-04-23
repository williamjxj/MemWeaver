"""Ingest → query roundtrip with mocked Ollama."""

import asyncio
from datetime import datetime, timezone
from pathlib import Path

import pytest

from server.config import Settings
from server.db.database import init_db
from server.pipeline import query_search
from server.pipeline.ingest_worker import IngestJob, run_ingest_pipeline


@pytest.fixture
def isolated_settings(tmp_path: Path) -> Settings:
    base = tmp_path / "mw"
    base.mkdir(parents=True, exist_ok=True)
    db = base / "t.db"
    wiki = base / "wiki"
    raw = base / "raw"
    s = Settings(
        db_path=db,
        wiki_dir=wiki,
        raw_dir=raw,
        dlq_dir=base / "failed",
        ollama_host="http://127.0.0.1:9",
        ollama_model="test-model",
        ollama_timeout=5.0,
    )
    asyncio.run(init_db(s))
    return s


@pytest.mark.asyncio
async def test_ingest_then_query_roundtrip(
    isolated_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = isolated_settings

    async def fake_json(
        host: str,
        model: str,
        prompt: str,
        timeout: float = 120.0,
    ) -> dict[str, object]:
        return {
            "atom": "RAG combines retrieval with generation.",
            "key_claims": ["retrieval augments context"],
            "detected_topics": ["rag"],
            "detected_entities": [],
        }

    async def fake_text(
        host: str,
        model: str,
        prompt: str,
        timeout: float = 120.0,
    ) -> str:
        return "## Summary\n\nRAG is retrieval-augmented generation.\n"

    monkeypatch.setattr(
        "server.pipeline.ingest_worker.ollama_generate_json",
        fake_json,
    )
    monkeypatch.setattr(
        "server.pipeline.ingest_worker.ollama_generate_text",
        fake_text,
    )

    job = IngestJob(
        ingest_id="ing_test_1",
        question="What is RAG?",
        answer="RAG uses a retriever plus an LLM.",
        source="test",
        session_id=None,
        tags=["nlp"],
        received_at=datetime.now(timezone.utc),
    )
    await run_ingest_pipeline(job, settings)

    rows = await query_search.search_pages(settings, "RAG", limit=5)
    assert len(rows) >= 1
    assert any("rag" in (r.get("path") or "").lower() for r in rows)
