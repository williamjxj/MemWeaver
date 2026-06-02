"""/chat must not auto-enqueue an ingest after streaming."""

import asyncio

from fastapi.testclient import TestClient

from server import main as m


def test_chat_does_not_enqueue_ingest(monkeypatch):
    async def noop_init_db(settings):
        return None

    async def noop_worker(queue, settings):
        while True:
            await asyncio.sleep(3600)

    monkeypatch.setattr(m, "init_db", noop_init_db)
    monkeypatch.setattr(m, "ingest_worker_loop", noop_worker)

    monkeypatch.setattr(
        m, "classify_topic", lambda q: ("general", ["general/user-preferences"])
    )

    async def fake_retrieve(question, slugs, cfg):
        return ("general/user-preferences", "wiki context")

    monkeypatch.setattr(m, "retrieve_summary", fake_retrieve)

    async def fake_stream(question, summary, cfg):
        yield "Hello"

    monkeypatch.setattr(m, "stream_chat", fake_stream)

    calls: list[tuple] = []

    async def spy_enqueue(*args, **kwargs):
        calls.append((args, kwargs))
        return {"status": "accepted", "ingest_id": "x", "message": "m"}

    monkeypatch.setattr(m.memory_api, "enqueue_ingest", spy_enqueue)

    with TestClient(m.app) as client:
        resp = client.post("/chat", json={"question": "hi"})
        assert resp.status_code == 200
        body = resp.text

    assert "event: done" in body
    assert calls == [], "/chat must not enqueue an ingest"
