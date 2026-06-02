# Documentation

This directory is organized into logical categories. See the sections below to find what you need.

---

## Project Definition & Analysis

- **[PRD](synthesis/prd.md)** — Original product requirements document
- **[Project Brief](synthesis/PROJECT_BRIEF.md)** — Current scope, decisions, and constraints
- **[Project Details](synthesis/PROJECT_DETAILS.md)** — Deep analysis, source map, risk assessment
- **[Evolving Thesis](synthesis/EVOLVING_THESIS.md)** — Running cross-source synthesis, open questions, decisions
- **[Known Gaps](known-gaps.md)** — Missing capabilities and improvement recommendations

## Architecture

- **[Architecture Decision Records](adr/)** — Key decisions in Context / Decision / Consequences format
  - `001` — Dual-LLM architecture
  - `002` — SQLite FTS5 over Postgres
  - `003` — SSE streaming pattern
  - `004` — Document management canonicalization

## Specs & Plans

- **[Design Specs](specs/)** — Detailed design documents for each feature
  - FastAPI skeleton, typed models & settings, chat frontend, MCP server, UI redesign, wiki graph view, two-tier LLM, opt-in save-to-memory
- **[Implementation Plans](plans/)** — Executable implementation plans per spec

## Guides & Methodology

- **[Collect → Distill → Ingest](guides/collect-distill-ingest.md)** — Multi-LLM knowledge distillation methodology
- **[Project Management](guides/project-management.md)** — GitHub workflow, ADR process, changelog conventions

## Topic Summaries

- **[Chat + Memory Workflow](topics/chat-memory-workflow.md)** — Core two-speed chat/memory loop
- **[Ingest + Retrieval Pipeline](topics/ingest-retrieval-pipeline.md)** — How the pipeline works end-to-end
- **[Document Management](topics/document-management.md)** — How docs are organized and maintained

## Research Sources (read-only)

Multi-LLM research outputs that informed the design. Preserved as immutable evidence.

- **[v1 — First pass](research/v1/)** — Claude, ChatGPT, Gemini raw responses
- **[v2 — Second pass](research/v2/)** — Revised plans with stronger implementation focus
- **[v3 — Third pass](research/v3/)** — DeepSeek, OpenCode, Copilot analysis & roadmaps

## Reference Material

- **[References](references/)** — Architecture diagrams, design inspiration, and background analysis

## External Links

- [Changelog](../CHANGELOG.md) — Release history
- [Roadmap](roadmap.md) — Milestone-level plan
