# Opt-in "Save to Memory" for Chat Q/A — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make saving a chat Q/A pair to `raw/qa/` opt-in per answer (with an optional freeform note), instead of auto-saving every `/chat` turn.

**Architecture:** Reuse the existing `POST /ingest` pipeline. Add an optional `note` field threaded into the raw JSON record. Remove the automatic end-of-stream ingest from `/chat`. In the frontend, render a per-answer "Save to memory" control that reveals a note textarea and calls `/ingest`.

**Tech Stack:** Python 3.12, FastAPI, pydantic v2, pytest; Next.js 16 (App Router, Tailwind), TypeScript.

---

## File Structure

| File | Responsibility |
|------|----------------|
| `server/models/api.py` | Add `note` to `IngestPayload` (modify) |
| `server/main.py` | Pass `note` to `enqueue_ingest`; remove `/chat` auto-ingest (modify) |
| `server/services/memory_api.py` | Add `note` param to `enqueue_ingest` (modify) |
| `server/pipeline/ingest_worker.py` | Add `note` to `IngestJob`; write it into `raw_doc` (modify) |
| `tests/test_note_ingest.py` | New backend tests: note persisted in raw JSON; enqueue threads note |
| `tests/test_chat_no_autosave.py` | New backend test: `/chat` does not enqueue ingest |
| `chat-app/lib/api.ts` | Add `saveQa(question, answer, note)` (modify) |
| `chat-app/components/SaveToMemory.tsx` | New per-answer save control |
| `chat-app/components/ChatWindow.tsx` | Render `SaveToMemory` under completed assistant messages (modify) |
| `chat-app/app/page.tsx` | Add `handleSaveQa`, pass to `ChatWindow` (modify) |

---

## Task 1: Thread `note` through the ingest path

**Files:**
- Modify: `server/models/api.py` (`IngestPayload`)
- Modify: `server/pipeline/ingest_worker.py` (`IngestJob`, `raw_doc`)
- Modify: `server/services/memory_api.py` (`enqueue_ingest`)
- Modify: `server/main.py` (`/ingest` route)
- Test: `tests/test_note_ingest.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_note_ingest.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./venv/bin/pytest tests/test_note_ingest.py -v`
Expected: FAIL — `IngestJob` has no `note` parameter (TypeError) and/or `enqueue_ingest` rejects `note`.

- [ ] **Step 3: Add `note` to `IngestPayload`**

In `server/models/api.py`, in `IngestPayload` (after `tags`):

```python
    tags: list[str] = Field(default_factory=list)
    note: str | None = None
    timestamp: datetime | None = None
```

- [ ] **Step 4: Add `note` to `IngestJob` and write it to `raw_doc`**

In `server/pipeline/ingest_worker.py`, add to the `IngestJob` dataclass (after `tags`):

```python
    tags: list[str]
    received_at: datetime
    note: str | None = None
```

(`received_at` stays where it is; `note` is added as the last field with a default so existing positional constructions keep working.)

Then in `run_ingest_pipeline`, in the `raw_doc` dict, add a `"note"` key (e.g. after `"session_id"`):

```python
        "session_id": job.session_id,
        "note": job.note,
        "original": {"question": job.question, "answer": job.answer},
```

- [ ] **Step 5: Add `note` param to `enqueue_ingest`**

In `server/services/memory_api.py`, update the signature and the `IngestJob(...)` construction:

```python
async def enqueue_ingest(
    settings: Settings,
    queue: asyncio.Queue[IngestJob],
    *,
    question: str,
    answer: str,
    source: str = "mcp",
    tags: list[str] | None = None,
    session_id: str | None = None,
    received_at: datetime | None = None,
    note: str | None = None,
) -> dict[str, str]:
```

and:

```python
    job = IngestJob(
        ingest_id=ingest_id,
        question=q,
        answer=a,
        source=source,
        session_id=session_id,
        tags=tags or [],
        received_at=received,
        note=note,
    )
```

- [ ] **Step 6: Pass `note` from the `/ingest` route**

In `server/main.py`, in the `ingest()` handler's `memory_api.enqueue_ingest(...)` call, add:

```python
            tags=payload.tags,
            session_id=payload.session_id,
            note=payload.note,
            received_at=received,
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `./venv/bin/pytest tests/test_note_ingest.py -v`
Expected: PASS (2 passed).

- [ ] **Step 8: Commit**

```bash
git add server/models/api.py server/pipeline/ingest_worker.py server/services/memory_api.py server/main.py tests/test_note_ingest.py
git commit -m "feat: thread optional note through ingest into raw/qa JSON"
```

---

## Task 2: Remove `/chat` auto-ingest

**Files:**
- Modify: `server/main.py` (`/chat` route — remove the Phase-B enqueue block)
- Test: `tests/test_chat_no_autosave.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_chat_no_autosave.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/bin/pytest tests/test_chat_no_autosave.py -v`
Expected: FAIL — `calls` is non-empty because `/chat` still calls `enqueue_ingest` after streaming.

- [ ] **Step 3: Remove the Phase-B enqueue block**

In `server/main.py`, inside the `chat()` route's `event_stream()`, delete the trailing background-compilation block so the generator ends right after the `done` event. Remove exactly this block:

```python
        # Phase B: enqueue wiki compilation in the background
        if full_answer.strip():
            try:
                await memory_api.enqueue_ingest(
                    cfg,
                    app.state.ingest_queue,
                    question=req.question.strip(),
                    answer=full_answer.strip(),
                    source="chat",
                    tags=[topic],
                )
            except Exception:
                logger.exception("failed to enqueue background compilation for chat")
```

Leave the `yield ... event: done ...` as the final statement of `event_stream()`. Do not change the `/ingest` route's use of `memory_api.enqueue_ingest`.

- [ ] **Step 4: Run test to verify it passes**

Run: `./venv/bin/pytest tests/test_chat_no_autosave.py -v`
Expected: PASS (1 passed).

- [ ] **Step 5: Confirm the app still imports**

Run: `./venv/bin/python -c "import server.main"`
Expected: no error.

- [ ] **Step 6: Commit**

```bash
git add server/main.py tests/test_chat_no_autosave.py
git commit -m "feat: stop auto-saving chat turns; saving is now opt-in"
```

---

## Task 3: Frontend `saveQa` API helper

**Files:**
- Modify: `chat-app/lib/api.ts`

- [ ] **Step 1: Add `saveQa`**

In `chat-app/lib/api.ts`, after `streamChat` (before `fetchWikiContent`), add:

```typescript
export async function saveQa(
  question: string,
  answer: string,
  note: string,
): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/ingest`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        answer,
        note: note || null,
        source: "chat",
      }),
    });
    return res.ok;
  } catch {
    return false;
  }
}
```

- [ ] **Step 2: Verify the frontend type-checks / builds**

Run: `cd chat-app && pnpm build`
Expected: build succeeds (no TypeScript errors from the new function).

- [ ] **Step 3: Commit**

```bash
git add chat-app/lib/api.ts
git commit -m "feat(chat-app): add saveQa helper to POST /ingest"
```

---

## Task 4: `SaveToMemory` component

**Files:**
- Create: `chat-app/components/SaveToMemory.tsx`

- [ ] **Step 1: Create the component**

Create `chat-app/components/SaveToMemory.tsx`:

```tsx
"use client";

import { useState } from "react";

interface SaveToMemoryProps {
  onSave: (note: string) => Promise<boolean>;
}

export function SaveToMemory({ onSave }: SaveToMemoryProps) {
  const [checked, setChecked] = useState(false);
  const [note, setNote] = useState("");
  const [status, setStatus] = useState<"idle" | "saving" | "saved" | "error">("idle");

  if (status === "saved") {
    return <div className="mt-1 text-xs text-green-600">Saved ✓</div>;
  }

  async function handleSave() {
    setStatus("saving");
    const ok = await onSave(note.trim());
    setStatus(ok ? "saved" : "error");
  }

  return (
    <div className="mt-1 flex flex-col gap-1">
      <label className="flex items-center gap-1.5 text-xs text-muted-foreground cursor-pointer">
        <input
          type="checkbox"
          checked={checked}
          onChange={(e) => setChecked(e.target.checked)}
          className="accent-primary"
        />
        Save to memory
      </label>
      {checked && (
        <div className="flex flex-col gap-1">
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Optional note / metadata…"
            rows={2}
            className="border rounded-md px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-primary"
          />
          <div className="flex items-center gap-2">
            <button
              onClick={handleSave}
              disabled={status === "saving"}
              className="px-2 py-1 bg-primary text-primary-foreground rounded-md text-xs hover:opacity-90 disabled:opacity-50"
            >
              {status === "saving" ? "Saving…" : "Save"}
            </button>
            {status === "error" && (
              <span className="text-xs text-destructive">Save failed — try again</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify build**

Run: `cd chat-app && pnpm build`
Expected: build succeeds.

- [ ] **Step 3: Commit**

```bash
git add chat-app/components/SaveToMemory.tsx
git commit -m "feat(chat-app): add SaveToMemory per-answer control"
```

---

## Task 5: Wire `SaveToMemory` into the chat view

**Files:**
- Modify: `chat-app/components/ChatWindow.tsx`
- Modify: `chat-app/app/page.tsx`

- [ ] **Step 1: Extend `ChatWindow` to render the control**

In `chat-app/components/ChatWindow.tsx`:

Add the import at the top:

```tsx
import { MessageBubble } from "./MessageBubble";
import { SaveToMemory } from "./SaveToMemory";
```

Add `onSaveQa` to `ChatWindowProps`:

```tsx
interface ChatWindowProps {
  messages: Message[];
  isStreaming: boolean;
  onSend: (question: string) => void;
  onStop?: () => void;
  onSaveQa?: (question: string, answer: string, note: string) => Promise<boolean>;
}
```

Destructure it:

```tsx
export function ChatWindow({
  messages,
  isStreaming,
  onSend,
  onStop,
  onSaveQa,
}: ChatWindowProps) {
```

Replace the `messages.map(...)` block with one that renders the control under completed assistant messages:

```tsx
        {messages.map((m, i) => {
          const isLast = i === messages.length - 1;
          const streamingThis = isStreaming && isLast && m.role === "assistant";
          const showSave =
            m.role === "assistant" && !!m.content && !streamingThis && !!onSaveQa;
          const question = i > 0 ? messages[i - 1].content : "";
          return (
            <div key={m.id} className="space-y-1">
              <MessageBubble
                role={m.role}
                content={m.content}
                isStreaming={streamingThis}
              />
              {showSave && (
                <div className="flex justify-start">
                  <div className="max-w-[75%]">
                    <SaveToMemory
                      onSave={(note) => onSaveQa!(question, m.content, note)}
                    />
                  </div>
                </div>
              )}
            </div>
          );
        })}
```

- [ ] **Step 2: Provide the handler in `page.tsx`**

In `chat-app/app/page.tsx`:

Add `saveQa` to the import from `@/lib/api`:

```tsx
import { streamChat, fetchWikiContent, fetchWikiTree, saveQa, type ChatDoneData, type WikiTreeNode } from "@/lib/api";
```

Add a handler (near `handleSend`):

```tsx
  async function handleSaveQa(question: string, answer: string, note: string): Promise<boolean> {
    return saveQa(question, answer, note);
  }
```

Pass it to the `ChatWindow` instance:

```tsx
          <ChatWindow
            messages={messages}
            isStreaming={isStreaming}
            onSend={handleSend}
            onStop={handleStop}
            onSaveQa={handleSaveQa}
          />
```

- [ ] **Step 3: Verify build**

Run: `cd chat-app && pnpm build`
Expected: build succeeds, no type errors.

- [ ] **Step 4: Commit**

```bash
git add chat-app/components/ChatWindow.tsx chat-app/app/page.tsx
git commit -m "feat(chat-app): show Save-to-memory under completed answers"
```

---

## Task 6: End-to-end verification (manual)

**Files:** none.

- [ ] **Step 1: Backend suite**

Run: `./venv/bin/pytest tests/ -q`
Expected: the two new test files pass; no NEW failures vs. the pre-existing `test_contradictions.py::test_maybe_prepend_skips_when_empty_existing` failure (which is unrelated and also fails on `main`).

- [ ] **Step 2: Manual smoke (requires backend + Ollama + DeepSeek key, and `chat-app` running)**

Start backend (`./venv/bin/uvicorn server.main:app --reload`) and frontend (`cd chat-app && pnpm dev`).
1. Ask a question; confirm the answer streams.
2. Confirm a new `raw/qa/<today>/…json` is NOT created automatically (auto-save removed).
3. Under the answer, check "Save to memory", type a note, click Save.
4. Confirm "Saved ✓" appears, a new `raw/qa/<today>/<id>.json` exists, and its `note` field matches what you typed.

---

## Self-Review Notes

- **Spec coverage:** note field end-to-end (Task 1), auto-save removal (Task 2), `saveQa` (Task 3), `SaveToMemory` control with default-off + saved-lock + error state (Task 4), wiring with paired question (Task 5), verification (Task 6).
- **Type consistency:** `note: str | None` (backend) ↔ `note: note || null` (frontend). `saveQa(question, answer, note) => Promise<boolean>` matches `SaveToMemory.onSave: (note) => Promise<boolean>` via `ChatWindow.onSaveQa`. `IngestJob.note` default keeps existing positional constructions (integration test, etc.) valid.
- **No-placeholder check:** all steps contain concrete code/commands.
- **Scope:** raw-only note; SQLite/FTS/prompts untouched; no new endpoint.
