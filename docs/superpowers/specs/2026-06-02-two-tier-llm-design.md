# Two-Tier LLM Split — Design Doc

**Date:** 2026-06-02  
**Status:** Approved  
**Stack:** FastAPI · Python 3.12 · httpx (async) · DeepSeek API (OpenAI-compatible) · Ollama (local)

---

## 1. Overview

Split the single LLM (currently `qwen2.5:7b-instruct` for everything) into **two tiers**:

| Tier | Model | Role |
|------|-------|------|
| Public chat LLM | DeepSeek `deepseek-v4-flash` (hosted, OpenAI-compatible API) | The user-facing `/chat` answer |
| Local pipeline LLM | Ollama `qwen2.5:7b-instruct` | Q/A distill + llm-wiki page generation (and other internal calls) |

The embedding model (`nomic-embed-text` via Ollama) is unchanged.

### Key decisions (brainstorming outcomes)

| Decision | Choice |
|----------|--------|
| Chat API protocol | **OpenAI-compatible** — `POST` directly to `DEEPSEEK_BASE_URL` (the full `.../v1/chat/completions` endpoint), `stream:true` (SSE), raw `httpx` |
| Scope of DeepSeek | **`/chat` only** — distill, wiki-gen, classifier fallback, contradiction check, query synthesis all stay on local Ollama |
| Failure behavior | **Error, no fallback/retry** — emit existing SSE `event: error` and stop |
| Code structure | **Approach A** — dedicated `deepseek_client.py`; `public_llm.py` rewired to delegate to it |
| `/health` | Unchanged (Ollama + DB only) |

### Success criteria

1. `POST /chat` streams tokens from DeepSeek `deepseek-v4-flash`, with wiki context injected as a `system` message.
2. Background ingest after a chat turn still runs the local Ollama pipeline (distill → wiki page → SQLite/FTS → embed).
3. `/query`, `/ingest`, classifier fallback, and contradiction checks still call local Ollama `qwen2.5:7b-instruct`.
4. DeepSeek failure surfaces as an SSE `error` event; no crash, background ingest skipped.
5. Unit tests cover the DeepSeek SSE parser and the system/user message mapping.

---

## 2. Configuration

Add to `server/config/settings.py`:

```python
deepseek_api_key: str = Field(default="")
deepseek_model: str = Field(default="deepseek-v4-flash")
deepseek_base_url: str = Field(default="https://api.deepseek.com/v1/chat/completions")
```

- Env vars: `DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL`, `DEEPSEEK_BASE_URL`. All three already exist in `.env`.
- **`DEEPSEEK_BASE_URL` is the full chat-completions endpoint** (`https://api.deepseek.com/v1/chat/completions`). The client POSTs directly to it — it does **not** append a path.
- `OLLAMA_*` unchanged — `OLLAMA_MODEL=qwen2.5:7b-instruct` remains the pipeline model.
- `.env.example` documents the three new vars with a placeholder key (never the real key).
- `.env` is gitignored (verified) — the real key stays local.

---

## 3. Components

| Component | Change |
|-----------|--------|
| `server/services/deepseek_client.py` | **New.** `stream_deepseek_chat(question, wiki_summary, settings) -> AsyncGenerator[str, None]`. POSTs directly to `settings.deepseek_base_url` with `stream:true`, header `Authorization: Bearer {deepseek_api_key}`. Body: model `deepseek_model`, messages `[system: WIKI_INJECTION_TEMPLATE(summary) (omitted if empty), user: question]`, `temperature` ~0.2, `max_tokens` ~256. Parses OpenAI SSE: each `data: {...}` line → `choices[0].delta.content`; stops on `data: [DONE]`. |
| `server/services/public_llm.py` | **Rewired.** Keeps `WIKI_INJECTION_TEMPLATE`. Builds the system/user messages and delegates streaming to `deepseek_client`. The entry point is **renamed `stream_ollama_chat` → `stream_chat`**, and `main.py`'s import + call site are updated accordingly. |
| `server/main.py` `/chat` | Same flow (classify → retrieve_summary → stream → enqueue background ingest). Only the streaming target changes; RAG context injection preserved. |
| `server/ollama/client.py`, `ingest_worker.py`, `classifier.py`, `contradictions.py`, `query_search.py` | **Untouched** — still `qwen2.5:7b-instruct`. |
| `server/pipeline/embedder.py` | **Untouched** — still `nomic-embed-text`. |

---

## 4. Data Flow (chat request)

```
POST /chat
  → classify_topic (+ Ollama fallback on local qwen)    [local]
  → retrieve_summary (keyword RAG over wiki/_index.md)   [local files]
  → stream_deepseek_chat(question, summary)              [DEEPSEEK cloud]
       system: WIKI_INJECTION_TEMPLATE(summary)
       user:   question
       SSE delta tokens → client
  → on done: enqueue_ingest(question, full_answer)       [→ local Ollama pipeline]
       distill (qwen) → wiki page (qwen) → SQLite/FTS → embed (nomic)
```

A single chat turn touches **DeepSeek** (live answer) and later **Ollama** (background distill + wiki page from that same answer).

---

## 5. Error Handling

- DeepSeek request failure (network, rate limit, non-2xx) → emit existing `event: error` SSE frame and stop. `full_answer` stays empty, so background ingest is skipped.
- Missing `DEEPSEEK_API_KEY` → fail fast with a clear error on `/chat`.
- No retry, no Ollama fallback (explicit decision).

---

## 6. Testing

- `tests/test_deepseek_client.py` — feed canned OpenAI SSE chunks (incl. `[DONE]` and a non-content keepalive) to a mocked `httpx` stream; assert the yielded token sequence.
- `public_llm` message-mapping test — wiki summary → system message; question → user message; empty summary → no system message.
- Update existing `/chat` test(s) that mock the streamer to mock the new path.
- Pipeline/distill/wiki tests unchanged (still Ollama).

---

## 7. Out of Scope / Follow-ups

- DeepSeek health check in `/health` (left unchanged for now).
- Doc cleanup: `AGENTS.md`, `CLAUDE.md`, `.cursorrules` still describe a single Ollama model and disagree on its name — optional small update alongside this change.
