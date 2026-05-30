# MemWeaver

> A dual-LLM memory pipeline that uses a public LLM for fast reasoning and local Ollama for background LLM-Wiki and Agent Skills compilation, targeting Memory Compression + Knowledge Distillation + Retrieval.

MemWeaver is a **local-first, memory-augmented chat** system. It compiles conversations into a persistent wiki that your LLM reads from and writes to, so every answer is informed by accumulated knowledge — not just the current chat history.

- **Local privacy** — Raw Q&A stays on your machine. Ollama runs locally.
- **Human-readable storage** — All memory is stored as Markdown in a wiki vault, editable in Obsidian or any editor.
- **Hybrid search** — FTS5 keyword search + vector embeddings (sqlite-vec) merged via RRF (Reciprocal Rank Fusion).
- **Agent integration** — Exposes MCP (Model Context Protocol) tools so coding agents can read/write memory mid-session.

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│  Browser (http://localhost:3000)                          │
│  ┌──────────────────┐    ┌─────────────────────────────┐  │
│  │   ChatWindow      │    │   Dashboard (sidebar)       │  │
│  │   (messages +     │    │   - Active Context          │  │
│  │    input bar)     │    │   - History                 │  │
│  └────────┬─────────┘    │   - Wiki Tree               │  │
│           │              │   - Knowledge Graph          │  │
│           │ POST /api/chat│   - System Status           │  │
│           │ (SSE proxy)  └──────────────────────────────┘  │
└───────────┼──────────────────────────────────────────────┘
            │
            ▼
┌──────────────────────────────────────────────────────────┐
│  FastAPI Backend (localhost:8000)                          │
│                                                            │
│  POST /chat ──► classify question                         │
│       │          └─► retrieve compiled wiki context       │
│       │          └─► stream LLM answer (SSE)              │
│       │          └─► [background] compile Q&A into wiki   │
│                                                            │
│  POST /ingest ──► queue Q&A for async wiki compilation    │
│  GET  /query  ──► FTS5 + vector hybrid search (RRF)      │
│  GET  /wiki/{slug} ──► read wiki markdown page           │
│  GET  /health ──► service status                          │
│  GET  /stats  ──► counters & metrics                      │
│                                                            │
│  MCP stdio ──► wiki_search / wiki_ingest /                │
│                wiki_get_page / wiki_stats                  │
└──────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites

- **Python 3.12+**
- **Node.js 20+** and **pnpm**
- **Ollama** running locally with a model pulled

### Backend

```bash
git clone https://github.com/williamjxj/MemWeaver.git
cd MemWeaver
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn server.main:app --reload
```

### Frontend

```bash
cd chat-app
pnpm install
pnpm dev    # → http://localhost:3000
```

### Smoke test

```bash
./scripts/smoke-check.sh
```

---

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/chat` | POST | Stream chat with wiki-augmented context (SSE) |
| `/ingest` | POST | Queue Q/A pairs for async wiki compilation |
| `/query` | GET | Hybrid search (`?mode=keyword\|semantic\|hybrid`) |
| `/wiki/{slug}` | GET | Fetch a wiki page by slug |
| `/health` | GET | Service health check |
| `/stats` | GET | Aggregate counters and usage metrics |

---

## MCP Tools (IDE Integration)

The server exposes MCP tools over stdio for IDE integration:

| Tool | Description |
|------|-------------|
| `wiki_search` | Hybrid FTS5 + vector search over compiled wiki |
| `wiki_ingest` | Save Q/A to async wiki compile pipeline |
| `wiki_get_page` | Fetch full markdown by slug |
| `wiki_stats` | Vault counters + Ollama reachability |

---

## Project Structure

```
MemWeaver/
├── server/                  # FastAPI backend
│   ├── main.py              # Route definitions
│   ├── config/settings.py   # Runtime config
│   ├── models/api.py        # Pydantic schemas
│   ├── db/                  # SQLite + FTS5 + vec0
│   ├── pipeline/            # Ingest, embed, search
│   └── services/            # Classifier, wiki retriever
├── chat-app/                # Next.js 16 frontend
│   ├── app/page.tsx         # Main chat page
│   ├── components/          # UI components
│   └── app/api/chat/        # SSE proxy route
├── wiki/                    # LLM wiki markdown vault
├── raw/                     # Immutable ingest JSON
├── docs/                    # Design docs & ADRs
└── tests/                   # Python test suite
```

---

## Features

| Feature | Status | Notes |
|---------|--------|-------|
| Chat with wiki context | ✅ | SSE streaming, auto-wiki compile |
| Q&A ingestion | ✅ | Async queue + background worker |
| FTS5 full-text search | ✅ | SQLite FTS5 |
| Semantic search | ✅ | sqlite-vec embeddings |
| Hybrid search (RRF) | ✅ | Reciprocal Rank Fusion |
| MCP server | ✅ | IDE integration tools |
| Knowledge graph | ⏳ | Flat wikilinks, in progress |
| Value gate | ⏳ | Skip low-value compilations |
| Temporal validity | 📅 | Planned |
| Memory taxonomy | 📅 | Episodic/semantic/procedural |
| Cloud LLM support | 📅 | Optional hosted provider |

---

## Development

```bash
# Run tests
./venv/bin/pytest tests/ -v

# Build frontend
cd chat-app && pnpm build

# Custom config
APP_ENV=development HOST=127.0.0.1 PORT=8000 uvicorn server.main:app --reload
```

---

## Related Docs

- [Architecture Decisions](https://github.com/williamjxj/MemWeaver/tree/main/docs/adr/)
- [Roadmap](https://github.com/williamjxj/MemWeaver/blob/main/docs/roadmap.md)
- [Changelog](https://github.com/williamjxj/MemWeaver/blob/main/CHANGELOG.md)
