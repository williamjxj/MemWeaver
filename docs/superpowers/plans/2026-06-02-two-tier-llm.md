# Two-Tier LLM Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Route the user-facing `/chat` endpoint to the hosted DeepSeek `deepseek-v4-flash` model (OpenAI-compatible streaming) while keeping all background pipeline calls (distill, wiki generation, classifier fallback, contradiction check, query synthesis) on the local Ollama `qwen2.5:7b-instruct` model.

**Architecture:** Add a dedicated `deepseek_client.py` that POSTs directly to the full DeepSeek chat-completions endpoint and yields tokens parsed from OpenAI SSE chunks. Rewire `public_llm.py` to build OpenAI-style `system`/`user` messages (wiki context → system) and delegate streaming to that client. `main.py`'s `/chat` flow is unchanged except for the renamed streamer call. Nothing in the Ollama pipeline changes.

**Tech Stack:** Python 3.12, FastAPI, httpx (async streaming), pydantic-settings, DeepSeek API (OpenAI-compatible), pytest + pytest-asyncio.

---

## File Structure

| File | Responsibility |
|------|----------------|
| `server/config/settings.py` | Add `deepseek_api_key`, `deepseek_model`, `deepseek_base_url` fields (modify) |
| `.env.example` | Document the three new DeepSeek vars (modify) |
| `server/services/deepseek_client.py` | **New.** Pure SSE token extractor `_extract_token` + async generator `stream_deepseek_chat` |
| `server/services/public_llm.py` | Build OpenAI messages (`build_messages`), delegate to deepseek_client, rename `stream_ollama_chat` → `stream_chat` (modify) |
| `server/main.py` | Update import + call site to `stream_chat` (modify) |
| `tests/test_deepseek_client.py` | **New.** Unit tests for `_extract_token` |
| `tests/test_public_llm.py` | **New.** Unit tests for `build_messages` |

---

## Task 1: DeepSeek settings + env docs

**Files:**
- Modify: `server/config/settings.py:16-19`
- Modify: `.env.example`

- [ ] **Step 1: Add DeepSeek fields to `Settings`**

In `server/config/settings.py`, after the existing `ollama_api_key` field (line 19), add:

```python
    deepseek_api_key: str = Field(default="")
    deepseek_model: str = Field(default="deepseek-v4-flash")
    deepseek_base_url: str = Field(
        default="https://api.deepseek.com/v1/chat/completions"
    )
```

Note: `deepseek_base_url` is the **full** chat-completions endpoint — the client POSTs directly to it and does not append a path.

- [ ] **Step 2: Document the vars in `.env.example`**

Add to `.env.example` (above the `OLLAMA_HOST` block):

```bash
# DeepSeek (public chat LLM). base_url is the FULL chat-completions endpoint.
DEEPSEEK_API_KEY=sk-your-key-here
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1/chat/completions
```

Do NOT put a real key here.

- [ ] **Step 3: Verify settings load**

Run: `./venv/bin/python -c "from server.config import get_settings; s=get_settings(); print(s.deepseek_model, s.deepseek_base_url)"`
Expected: prints `deepseek-v4-flash https://api.deepseek.com/v1/chat/completions` (or your `.env` overrides).

- [ ] **Step 4: Commit**

```bash
git add server/config/settings.py .env.example
git commit -m "feat: add DeepSeek settings for public chat LLM"
```

---

## Task 2: DeepSeek SSE client

**Files:**
- Create: `server/services/deepseek_client.py`
- Test: `tests/test_deepseek_client.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_deepseek_client.py`:

```python
"""Tests for the DeepSeek OpenAI-compatible SSE parser."""

from server.services.deepseek_client import _extract_token, _DONE


def test_extract_content_token():
    line = 'data: {"choices":[{"delta":{"content":"Hello"}}]}'
    assert _extract_token(line) == "Hello"


def test_extract_done_sentinel():
    assert _extract_token("data: [DONE]") is _DONE


def test_extract_blank_line_returns_none():
    assert _extract_token("") is None
    assert _extract_token("   ") is None


def test_extract_keepalive_or_role_chunk_returns_none():
    # role-only delta (first chunk) has no content
    line = 'data: {"choices":[{"delta":{"role":"assistant"}}]}'
    assert _extract_token(line) is None


def test_extract_non_data_line_returns_none():
    assert _extract_token(": keep-alive") is None


def test_extract_malformed_json_returns_none():
    assert _extract_token("data: {not json}") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/bin/pytest tests/test_deepseek_client.py -v`
Expected: FAIL with `ModuleNotFoundError` / `ImportError` (module not yet created).

- [ ] **Step 3: Write minimal implementation**

Create `server/services/deepseek_client.py`:

```python
"""Streaming DeepSeek client (OpenAI-compatible) for the /chat endpoint."""

import json
import logging
from typing import Any, AsyncGenerator

import httpx

from server.config import Settings

logger = logging.getLogger(__name__)

# Sentinel returned by _extract_token when the stream signals completion.
_DONE = object()


def _extract_token(line: str) -> Any:
    """Parse one OpenAI-style SSE line.

    Returns the content string, the _DONE sentinel on completion, or None
    for lines that carry no content (blank, comments, role-only deltas,
    or unparseable JSON).
    """
    line = line.strip()
    if not line or not line.startswith("data:"):
        return None
    payload = line[len("data:"):].strip()
    if payload == "[DONE]":
        return _DONE
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return None
    try:
        content = data["choices"][0]["delta"].get("content")
    except (KeyError, IndexError, TypeError):
        return None
    return content or None


async def stream_deepseek_chat(
    messages: list[dict[str, str]],
    settings: Settings,
) -> AsyncGenerator[str, None]:
    """Stream assistant text tokens from DeepSeek's chat-completions endpoint.

    POSTs directly to settings.deepseek_base_url (the full endpoint URL).
    """
    body = {
        "model": settings.deepseek_model,
        "messages": messages,
        "stream": True,
        "temperature": 0.2,
        "max_tokens": 256,
    }
    headers = {"Content-Type": "application/json"}
    if settings.deepseek_api_key:
        headers["Authorization"] = f"Bearer {settings.deepseek_api_key}"

    async with httpx.AsyncClient(timeout=settings.ollama_timeout) as client:
        async with client.stream(
            "POST", settings.deepseek_base_url, json=body, headers=headers
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                token = _extract_token(line)
                if token is _DONE:
                    return
                if token:
                    yield token
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./venv/bin/pytest tests/test_deepseek_client.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add server/services/deepseek_client.py tests/test_deepseek_client.py
git commit -m "feat: add DeepSeek SSE streaming client"
```

---

## Task 3: Rewire public_llm to DeepSeek

**Files:**
- Modify: `server/services/public_llm.py` (full rewrite of the streaming function)
- Test: `tests/test_public_llm.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_public_llm.py`:

```python
"""Tests for OpenAI-message construction in public_llm."""

from server.services.public_llm import build_messages, WIKI_INJECTION_TEMPLATE


def test_build_messages_with_summary():
    msgs = build_messages("What is RAG?", "RAG = retrieval augmented generation")
    assert msgs[0]["role"] == "system"
    assert "RAG = retrieval augmented generation" in msgs[0]["content"]
    assert msgs[-1] == {"role": "user", "content": "What is RAG?"}
    assert len(msgs) == 2


def test_build_messages_without_summary():
    msgs = build_messages("Hello", "")
    assert msgs == [{"role": "user", "content": "Hello"}]


def test_build_messages_whitespace_summary_is_skipped():
    msgs = build_messages("Hello", "   \n  ")
    assert len(msgs) == 1
    assert msgs[0]["role"] == "user"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/bin/pytest tests/test_public_llm.py -v`
Expected: FAIL with `ImportError: cannot import name 'build_messages'`.

- [ ] **Step 3: Write minimal implementation**

Replace the entire contents of `server/services/public_llm.py` with:

```python
"""Public-LLM chat streaming for /chat: builds OpenAI messages with wiki
context and delegates to the DeepSeek client."""

from typing import AsyncGenerator

from server.config import Settings
from server.services.deepseek_client import stream_deepseek_chat

WIKI_INJECTION_TEMPLATE = """\
You have structured background knowledge about this user and their projects. \
Use it as established context to give consistent, informed answers. \
Do not repeat this context back to the user.

--- Wiki Context ---
{summary}
---"""


def build_messages(question: str, wiki_summary: str) -> list[dict[str, str]]:
    """Build OpenAI chat messages. Wiki context becomes a system message
    (omitted when empty); the question is the user message."""
    messages: list[dict[str, str]] = []
    if wiki_summary.strip():
        messages.append(
            {
                "role": "system",
                "content": WIKI_INJECTION_TEMPLATE.format(summary=wiki_summary),
            }
        )
    messages.append({"role": "user", "content": question})
    return messages


async def stream_chat(
    question: str,
    wiki_summary: str,
    settings: Settings,
) -> AsyncGenerator[str, None]:
    """Stream DeepSeek tokens with wiki context injected as a system message."""
    messages = build_messages(question, wiki_summary)
    async for token in stream_deepseek_chat(messages, settings):
        yield token
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./venv/bin/pytest tests/test_public_llm.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add server/services/public_llm.py tests/test_public_llm.py
git commit -m "feat: route public_llm chat through DeepSeek with wiki context"
```

---

## Task 4: Wire /chat to the renamed streamer

**Files:**
- Modify: `server/main.py:33` (import) and `server/main.py:198` (call site)

- [ ] **Step 1: Update the import**

In `server/main.py`, change line 33 from:

```python
from server.services.public_llm import stream_ollama_chat
```

to:

```python
from server.services.public_llm import stream_chat
```

- [ ] **Step 2: Update the call site**

In `server/main.py` (inside `chat()`'s `event_stream`), change:

```python
            async for token in stream_ollama_chat(req.question, summary, cfg):
```

to:

```python
            async for token in stream_chat(req.question, summary, cfg):
```

- [ ] **Step 3: Verify no stale references remain**

Run: `rg "stream_ollama_chat" server tests`
Expected: no matches.

- [ ] **Step 4: Verify the app imports cleanly**

Run: `./venv/bin/python -c "import server.main"`
Expected: no error.

- [ ] **Step 5: Commit**

```bash
git add server/main.py
git commit -m "refactor: call renamed stream_chat in /chat route"
```

---

## Task 5: Full test suite + manual smoke verification

**Files:** none (verification only)

- [ ] **Step 1: Run the full unit suite**

Run: `./venv/bin/pytest tests/ -v`
Expected: all tests pass (existing tests that need live Ollama may be skipped/fail in their usual way — confirm no NEW failures are caused by these changes; the new `test_deepseek_client.py` and `test_public_llm.py` pass).

- [ ] **Step 2: Manual smoke test of /chat (requires real DEEPSEEK_API_KEY in .env and Ollama running)**

Start the server:

```bash
./venv/bin/uvicorn server.main:app --reload
```

In another terminal:

```bash
curl -N -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"What is mem-weaver in one sentence?"}'
```

Expected: SSE frames — a series of `event: token` lines streaming the DeepSeek answer, then one `event: done` frame with `wiki_slug`/`topic`/`context_chars`.

- [ ] **Step 3: Confirm background ingest still uses Ollama**

After the chat call completes, check that a new raw record was written and references the Ollama model:

Run: `ls -t raw/qa/$(date +%Y-%m-%d)/ | head -1`
Then read that file and confirm `"model": "qwen2.5:7b-instruct"`.
Expected: the background distill/wiki step ran on the local Ollama model, confirming the split.

- [ ] **Step 4: Negative test — DeepSeek failure surfaces as SSE error**

Temporarily set a bad key (`DEEPSEEK_API_KEY=sk-invalid` in env), restart, and repeat the curl from Step 2.
Expected: an `event: error` SSE frame with `{"message": "Ollama stream failed"}` (the existing generic error handler in `main.py`), and no crash.
Restore the real key afterward.

---

## Self-Review Notes

- **Spec coverage:** Config (Task 1), DeepSeek client + OpenAI SSE (Task 2), public_llm rewire + system/user mapping + rename (Task 3), `/chat` wiring (Task 4), tests + failure-path verification (Tasks 2/3/5). Ollama pipeline untouched (no task modifies it — by design). `/health` unchanged (out of scope per spec).
- **Type consistency:** `stream_deepseek_chat(messages, settings)` is defined in Task 2 and called in Task 3 with `build_messages(...)` output (a `list[dict[str,str]]`). `_DONE` is defined and imported by the test in Task 2. `stream_chat(question, wiki_summary, settings)` defined in Task 3, called in Task 4.
- **Error handling:** No retry/fallback (spec decision). `main.py`'s existing try/except around the stream converts any exception (incl. `httpx.HTTPStatusError` from `raise_for_status()`) into the `event: error` frame — verified in Task 5 Step 4.
