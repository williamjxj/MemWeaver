# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Two-tier LLM architecture**: `/chat` now routes through DeepSeek (SSE streaming) for public Q&A while Ollama backs the ingest pipeline, wiki compilation, and semantic embeddings. New `server/services/deepseek_client.py` and `server/services/public_llm.py` modules.
- **Wiki graph endpoint** `GET /wiki/graph` returns nodes (pages) and edges (wikilinks) for a force-directed graph view. Backed by `server/services/wiki_graph_api.py`.
- **Wiki tree endpoint** `GET /wiki/tree` returns a sidebar-friendly catalog from `wiki/index.md`. Backed by `server/services/wiki_tree_api.py`.
- **Dashboard UI**: Three-stage comparison panel (QA / RAG / LLM-Wiki) with stage tabs, widget-based dashboard (SystemStatus, ActiveContext, WikiTree, History), and D3 force-directed graph widget.
- **Opt-in save-to-memory**: Chat turns no longer auto-compile to the wiki. Users click a "Save to memory" checkbox (with optional note) to explicitly save. New `chat-app/components/SaveToMemory.tsx` and `saveQa` helper.
- **`note` field** on `POST /ingest` threaded through the pipeline into raw/qa JSON.
- **DeepSeek settings** `DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL`, `DEEPSEEK_BASE_URL` in pydantic-settings.
- **Wiki sidebar speed improvements** and MCP `wiki_search`/`wiki_get_page`/`wiki_ingest`/`wiki_stats` tools.
- **Backfill wikilinks script** `scripts/backfill_wikilinks.py` for generating wikilink relationships on existing pages.

### Changed
- Chat endpoint no longer auto-saves Q&A to wiki — saving is opt-in.
- Frontend redesigned with "Sage Garden" theme, SVG logo, favicon, and three-stage compare view.
- Frontend stage-tabs replace single-chat-window: Compare, QA Chat, RAG, LLM-Wiki.

### Fixed
- DeepSeek error handling and streaming loop termination.
- Graphify UI rendering issues.
- Document management canonicalization.
- Various UI responsiveness issues.

## [v0.1.0] - 2026-05-28

### Added
- FastAPI backend for ingesting Q/A pairs, querying wiki memory, streaming chat, and exposing health and stats endpoints.
- Async ingest pipeline that queues requests, compiles wiki pages, writes raw Q/A JSON, updates SQLite FTS tables, and builds semantic embeddings.
- MCP server entrypoint for IDE-integrated wiki search, ingest, page retrieval, and stats access.
- Next.js chat frontend with wiki-aware chat UI and API proxy routes.
- Local wiki vault structure with markdown concepts, index, and log files.

### Changed
- Standardized project structure around a single local wiki-memory workspace.

### Notes
- This tag marks the current working state of the repository at the time of release.

