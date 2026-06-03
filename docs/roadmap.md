# Roadmap

This roadmap tracks the project at a milestone level. For release history, see [CHANGELOG.md](../CHANGELOG.md). For architecture rationale, see [docs/adr](adr/).

## Milestone 0.1.0

Status: complete.

Delivered the current working state of the repository:

- FastAPI backend with `/ingest`, `/query`, `/chat`, `/health`, `/stats`, and `/wiki/{slug}`
- Async ingest queue and background worker
- SQLite persistence with FTS5 and semantic search support
- MCP server for IDE memory integration
- Next.js chat frontend and SSE proxy route
- Local wiki vault structure under `wiki/`

## Milestone 0.2.0

Status: in flight.

Delivered so far:

- **Two-tier LLM**: `/chat` streams via DeepSeek (SSE) for public Q&A; Ollama backs the ingest pipeline, wiki compilation, and semantic embeddings. `DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL`, `DEEPSEEK_BASE_URL` configured in settings.
- **Opt-in save-to-memory**: Chat turns no longer auto-compile to the wiki. Users click "Save to memory" (with optional note) to explicitly persist.
- **Wiki graph view**: `GET /wiki/graph` returns nodes + edges; `GET /wiki/tree` returns a sidebar catalog. Frontend includes a force-directed SVG graph widget in the Inventory tab.
- **Dashboard UI redesign**: 5-tab dashboard (Compare / QA Chat / RAG / LLM-Wiki / Inventory) with widget-based dashboard, Sage Garden theme, SVG logo, and favicon.
- **Inventory tab**: `GET /inventory` endpoint and frontend panel showing record counts across raw QA, wiki concepts, database tables, index, and log — with an expandable wiki graph card.
- **MCP server**: Standalone stdio MCP server with four wiki tools (`wiki_search`, `wiki_ingest`, `wiki_get_page`, `wiki_stats`) for IDE integration.
- **Document management**: Reorganized docs under `docs/references/`, updated ADRs, added CHANGELOG.

Remaining for 0.2.0:

- Add a value gate before compilation so low-value turns are skipped
- Tighten the wiki index format and make retrieval/indexing consistent
- Refine MCP and chat workflows so the two entry points stay aligned

## Later

Possible follow-up work once the current loop is stable:

- Memory taxonomy for episodic, semantic, and procedural knowledge
- Temporal validity for facts and claims
- Richer graph relationships beyond flat wikilinks
