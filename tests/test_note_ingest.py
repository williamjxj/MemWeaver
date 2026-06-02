"""note field flows through enqueue_ingest and into the raw/qa JSON record."""

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from server.config import Settings
from server.db.database import init_db
from server.pipeline.ingest_worker import IngestJob, run_ingest_pipeline
from server.services import memory_api


@pytest.fixture
def isolated_settings(tmp_path: Path) -> Settings:
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


@pytest.mark.asyncio
async def test_enqueue_ingest_threads_note(isolated_settings: Settings) -> None:
    queue: asyncio.Queue[IngestJob] = asyncio.Queue(maxsize=10)
    await memory_api.enqueue_ingest(
        isolated_settings,
        queue,
        question="What is RAG?",
        answer="Retrieval augmented generation.",
        source="chat",
        note="saved from chat UI",
    )
    job = queue.get_nowait()
    assert job.note == "saved from chat UI"


@pytest.mark.asyncio
async def test_run_ingest_pipeline_persists_note(
    isolated_settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = isolated_settings

    async def fake_json(host, model, prompt, timeout=120.0, api_key=""):
        return {
            "atom": "RAG combines retrieval with generation.",
            "key_claims": [],
            "detected_topics": ["rag"],
            "detected_entities": [],
        }

    async def fake_text(host, model, prompt, timeout=120.0, api_key=""):
        return "## Summary\n\nRAG.\n"

    monkeypatch.setattr("server.pipeline.ingest_worker.ollama_generate_json", fake_json)
    monkeypatch.setattr("server.pipeline.ingest_worker.ollama_generate_text", fake_text)

    received = datetime.now(timezone.utc)
    job = IngestJob(
        ingest_id="ing_note_1",
        question="What is RAG?",
        answer="A retriever plus an LLM.",
        source="chat",
        session_id=None,
        tags=[],
        received_at=received,
        note="my metadata note",
    )
    await run_ingest_pipeline(job, settings)

    day = received.astimezone(timezone.utc).strftime("%Y-%m-%d")
    raw_file = settings.raw_dir / day / "ing_note_1.json"
    data = json.loads(raw_file.read_text(encoding="utf-8"))
    assert data["note"] == "my metadata note"
