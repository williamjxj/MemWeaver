---
type: project-brief
status: current
date: 2026-05-29
export_cycle: 2
sources_ingested: 28
---

# Project Brief: mem-weaver

> Export cycle 2 · 28 sources ingested (27 LLM + 1 web) · 27 concept pages · Synced from wiki/synthesis/project-brief.md

## Problem

LLM chat is stateless: every turn either replays noisy raw history (token bloat, "lost in the middle") or starts fresh (no compounding knowledge). Developers building a "second brain" on a MacBook Pro need:

- **Persistent memory** that compiles over time, not a growing chat log
- **Local privacy** for raw Q+A, with optional cloud reasoning
- **Human-readable storage** (Markdown wiki) editable in Obsidian
- **Agent integration** so coding tools (Cursor, MCP clients) can read/write project memory mid-session

mem-weaver addresses this with a **dual-LLM memory pipeline**: local Ollama compiles conversations into a wiki; retrieval injects distilled summaries into answers instead of raw turns.

## Current Understanding

### Core loop

1. **Phase A (sync):** classify question → retrieve compiled wiki summary → LLM answers with summary as context (not raw history)
2. **Phase B (async):** Ollama incrementally merges Q+A into wiki pages after the user gets an answer

Follows **synthesis-first compilation** plus hybrid retrieval (FTS5 + sqlite-vec + RRF) at query time.

### Architecture

- **FastAPI middleware delegator:** `POST /ingest` (202 async), `GET /query` (FTS5 BM25), `POST /chat` (SSE), MCP stdio — **all implemented**
- **Storage triad:** SQLite (pages, qa_pairs, FTS5) + Markdown vault (Obsidian-compatible) + sqlite-vec embeddings
- **Entry points:** Next.js chat UI (designed) and MCP server (implemented) share `memory_api`
- **Epistemic foundation:** LLM outputs are synthetic first-pass knowledge — wiki distillation is where verified signal emerges

### As-built status

| Capability | Status |
|------------|--------|
| Milestone A (FastAPI skeleton) | **Done** |
| Milestone B (typed models) | **Done** |
| Phase 4 hardening (contradictions, DLQ, tests) | **Done** |
| Hybrid search (FTS5 + sqlite-vec + RRF) | **Done** |
| POST /chat (SSE) | **Done** |
| MCP server (stdio FastMCP, 4 tools) | **Done** |
| Value gate (SKIP/PROCESS in ingest) | **Missing** |
| `_index.md` vs `wiki/index.md` alignment | **Partial** |
| Cloud LLM client (Anthropic/OpenAI) | **Partial** (Ollama only) |

### Research workflow

Three independent LLMs converge on a unified workflow: **Collect → Ingest → Synthesize → Export → Apply → Closed Loop**. The wiki is the intermediate layer between multi-LLM research and implementation. Core concepts:
- **Context fragmentation** is the root problem; **context compression** (10k pages → 2 pages → prompts) is the moat
- **Multi-pass distillation:** raw → clustered → summarized → canonicalized → implementation-oriented
- **Contradictions tracking** is where multi-LLM input earns its keep
- **Human review gate** is non-negotiable between wiki and implementation

## Chosen Approach

### Firm decisions
- **Memory model:** Synthesis-first wiki compilation + hybrid retrieval
- **Pipeline:** Dual-LLM (Ollama compiler async + LLM reasoner with wiki context)
- **Storage:** SQLite + Markdown vault + sqlite-vec (NotebookLM validates SQLite+FTS5 over ChromaDB)
- **Entry points:** MCP (done) + Next.js chat (designed) share service layer
- **LLM source framing:** Synthetic first-pass signal, not ground truth
- **Knowledge compound:** Wiki is a compounding asset, not ephemeral RAG
- **Naming:** LLM-Wiki (2:1 over "context engine")
- **MVP scope:** Markdown + git; Obsidian as viewer; no custom app UI
- **Human gate:** Required between wiki distillation and dev context export

### Open decisions
- Index format: unify `_index.md` vs `wiki/index.md`
- Value gate: add SKIP/PROCESS before summarization
- Cloud LLM client: add Anthropic/OpenAI or keep Ollama-only
- Purpose steering: add `purpose.md` to prevent knowledge drift
- Decision records: adopt structured format with source attribution

## Constraints
- Single-user MacBook Pro — no multi-tenant or cloud scaling
- Ollama-only for local compilation
- The wiki is the pipeline — AGENTS.md schema governs format
- No vector DB dependency — SQLite + FTS5 + sqlite-vec is sufficient

## Non-Goals
- Multi-tenant memory scoping
- SaaS product / startup
- Typed entity-relationship knowledge graph (flat wikilinks)
- Temporal validity tracking
- Episodic/semantic/procedural memory taxonomy

## Rejected Alternatives
- Pure RAG (no wiki compile) — no persistent synthesis
- ChromaDB / external vector DB — unnecessary overhead for single-user
- Custom React app as primary UI — Obsidian + CLI sufficient for MVP
- "Context Engine" naming — 2:1 consensus for LLM-Wiki
- Open WebUI Pipelines — built dedicated FastAPI operator instead

## Open Questions
1. Entry point priority: Next.js chat UI next, or MCP polish for IDE workflow?
2. Automation pace: pipeline operator or stay manual?
3. Knowledge governance: implement confidence / supersession / review queue before hallucination write-back becomes critical?
4. Cloud LLM: add hosted Anthropic/OpenAI or keep local-first?
