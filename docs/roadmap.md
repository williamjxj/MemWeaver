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

Status: planned.

Focus areas:

- Add a value gate before compilation so low-value turns are skipped
- Tighten the wiki index format and make retrieval/indexing consistent
- Improve docs navigation and release discipline around ADRs and changelog entries
- Refine MCP and chat workflows so the two entry points stay aligned

## Later

Possible follow-up work once the current loop is stable:

- Memory taxonomy for episodic, semantic, and procedural knowledge
- Temporal validity for facts and claims
- Richer graph relationships beyond flat wikilinks
- Optional hosted cloud LLM support alongside local Ollama
