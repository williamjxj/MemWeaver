# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Planned release notes for the next milestone.

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

