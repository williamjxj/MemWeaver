# Chat App Frontend + `/chat` Backend — Design Doc

**Date:** 2026-05-11
**Status:** Approved
**Stack:** Next.js 14 (App Router) · TypeScript · Tailwind CSS · shadcn/ui · FastAPI · Ollama · SSE

---

## 1. Overview

Build a Next.js chat frontend (`chat-app/`) coupled with a new `/chat` streaming endpoint on the existing FastAPI backend. This implements the "Second Brain" vision from `docs/v2/2nd-brain-implementation.md` §7 — a chat UI where each question is augmented with relevant wiki memory before being sent to the LLM, and each answer is compiled back into the wiki in the background.

### Key decisions

- **Public LLM for /chat**: Ollama (local), fully offline. Reuses existing `server/ollama/client.py`.
- **Streaming**: Server-Sent Events (SSE) — tokens arrive one by one.
- **UI library**: shadcn/ui + Tailwind CSS.
- **App location**: `chat-app/` at repo root, alongside `server/`, `wiki/`, etc.
- **Scope**: Full-stack — new backend endpoints + frontend.

---

## 2. Architecture

### 2.1 System Diagram

```
┌─────────────────────────────────────────────────────┐
│                   Browser                            │
│  ┌──────────────────┐  ┌─────────────────────────┐  │
│  │   ChatWindow      │  │   WikiSidebar           │  │
│  │   (message list   │  │   (renders wiki .md     │  │
│  │    + input bar)   │  │    content)             │  │
│  └────────┬─────────┘  └────────▲────────────────┘  │
│           │ POST /api/chat       │ GET /wiki/{slug}  │
└───────────┼──────────────────────┼──────────────────┘
            │ (Next.js API route)  │
            ▼                      │
┌──────────────────────┐           │
│  Next.js Route:       │           │
│  /api/chat/route.ts   │           │
│  (proxies + forwards  │           │
│   SSE stream)         │           │
└──────────┬───────────┘           │
           │ POST /chat (SSE)      │
           ▼                       │
┌──────────────────────────────────┼──────────────────┐
│          FastAPI Backend                            │
│                                                     │
│  POST /chat ──► classifier.py ──► wiki_retriever.py │
│       │                    ──► public_llm.py (SSE)  │
│       │  (background)       ──► wiki compile        │
│       ▼                                             │
│  GET /wiki/{slug} ──► reads wiki/{slug}.md          │
└─────────────────────────────────────────────────────┘
```

### 2.2 Two-Phase Per-Turn Design

**Phase A (streaming, user-facing):**
User → ChatWindow → Next.js API route → FastAPI `/chat` → classify → retrieve wiki → Ollama (streaming) → tokens flow back → ChatWindow renders

**Phase B (async, after stream completes):**
FastAPI background task → value gate → merge Q&A into wiki article → update `_index.md`

---

## 3. Frontend Design

### 3.1 Component Tree

```
chat-app/
├── app/
│   ├── layout.tsx              ← Root layout (inter font, metadata)
│   ├── page.tsx                ← Main page: orchestrates ChatWindow + WikiSidebar
│   ├── globals.css             ← Tailwind imports, shadcn/ui CSS variables
│   └── api/
│       └── chat/route.ts       ← Route Handler: proxies POST to FastAPI /chat, relays SSE
├── components/
│   ├── ChatWindow.tsx          ← Message list + input bar
│   ├── WikiSidebar.tsx         ← Wiki article preview panel
│   ├── MessageBubble.tsx       ← Single message (user or assistant)
│   └── TopicBadge.tsx          ← Topic label pill
├── lib/
│   └── api.ts                  ← SSE fetch/stream parser
└── next.config.ts
```

### 3.2 Layout

Split-pane layout matching v2 spec §7:
- Chat takes `flex-1` (roughly 70%)
- WikiSidebar takes `w-80` (roughly 30%)

### 3.3 Data Flow

**Sending a message:**
1. User types question, hits Enter
2. `ChatWindow` calls `POST /api/chat` (Next.js API route) with `{ question }`
3. Next.js route forwards `POST http://localhost:8000/chat` with the same body
4. FastAPI returns SSE stream; Next.js route reads the stream and relays events to browser
5. Browser parses SSE `token` events and renders each chunk in a `MessageBubble` with `react-markdown` (GFM) for assistant messages; user messages stay as plain text
6. On `done` event: parse `wiki_slug`, `topic`, `context_chars` → update `WikiSidebar`
7. On `error` event: show error state in the message bubble

### 3.4 SSE Event Format

```
event: token\ndata: {"text": "The"}\n\n
event: token\ndata: {"text": " answer"}\n\n
event: done\ndata: {"wiki_slug": "coding/python-patterns", "topic": "coding", "context_chars": 1240}\n\n
event: error\ndata: {"message": "..."}\n\n
```

### 3.5 State Management

Simple React state in `page.tsx`. No external state library. Messages live only in memory (lost on refresh).

**Streaming state**: A single `isStreaming` boolean gates the streaming cursor. The accumulating answer is held in a local `fullAnswer` variable (not state) and written directly into the `messages` array on each token to avoid dead re-renders.

```typescript
interface Message { id: string; role: "user" | "assistant"; content: string; }
```

---

## 4. Backend Design

### 4.1 New Endpoints

**`POST /chat`** — Streaming chat with wiki memory injection. Returns SSE stream.

Implementation flow:
1. `classify_topic(question)` — keyword-based, returns `(topic, wiki_slugs)`
2. `retrieve_summary(question, candidates)` — reads `_index.md`, returns best matching article
3. Call Ollama with question + wiki context injected → stream tokens
4. After stream completes (background task): compile Q&A into the wiki via existing pipeline

**`GET /wiki/{slug}`** — Fetch wiki article. Returns `{ "slug": "...", "content": "..." }`.

### 4.2 New Service Modules

- **`server/services/classifier.py`** — Keyword topic classification (from v2 §4)
- **`server/services/wiki_retriever.py`** — Reads `_index.md`, scores articles by keyword overlap (v2 §6.2)
- **`server/services/public_llm.py`** — Streaming Ollama call with wiki injection

### 4.3 Streaming Implementation

FastAPI uses `StreamingResponse` with an async generator:

```python
from fastapi.responses import StreamingResponse

@app.post("/chat")
async def chat(req: ChatRequest):
    async def event_stream():
        async for chunk in stream_with_wiki(req.question):
            yield f"event: token\ndata: {json.dumps({'text': chunk})}\n\n"
        yield f"event: done\ndata: {json.dumps(done_event)}\n\n"
    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

---

## 5. Error Handling

| Failure mode | Frontend | Backend |
|---|---|---|
| Ollama not running | Error banner, disable send | SSE `error` event |
| Wiki article not found | Sidebar "No wiki context" | Return empty content |
| SSE stream interrupted | "Connection lost" bubble | N/A |
| Empty question | Disable Send button | 422 validation |
| `/chat` unavailable | Retry UI, timeout 30s | N/A |

---

## 6. Testing Strategy

- **Frontend**: Manual smoke via `pnpm dev` — send messages, verify streaming
- **Backend**: `curl` against `/chat` and `/wiki/{slug}`
- **Unit**: pytest for `classifier.py` and `wiki_retriever.py`
- **Integration**: Send question, verify wiki article created/updated

---

## 7. Future

- Message persistence (localStorage)
- Conversation history sidebar
- Settings panel (model selector, wiki toggle)
- Dark mode
