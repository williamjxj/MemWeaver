---
type: project-brief
status: draft
date: 2026-05-24
export_cycle: 1
sources_ingested: 22
---

# Project Brief: mem-weaver

## Docs

- [Docs home](README.md)
- [Roadmap](roadmap.md)
- [Changelog](../CHANGELOG.md)
- [Architecture Decisions](adr/)

> Export cycle 1 · 22 sources ingested · Draft — review before promoting to `current`

## Problem

LLM chat is stateless: every turn either replays noisy raw history (token bloat, "lost in the middle") or starts fresh (no compounding knowledge). Web UIs auto-accumulate full transcripts with no control over context. A developer building a personal "second brain" on a MacBook Pro needs:

- **Persistent memory** that compiles over time, not a growing chat log
- **Local privacy** for raw Q+A, with optional cloud reasoning
- **Human-readable storage** (Markdown wiki) editable in Obsidian
- **Agent integration** so coding tools (Cursor, MCP clients) can read/write project memory mid-session

mem-weaver addresses this with a **dual-LLM memory pipeline**: local Ollama compiles conversations into a wiki; retrieval injects distilled summaries into answers instead of raw turns. See [[dual-llm-memory-pipeline]] and [[memory-synthesis-vs-rag]].

## Current Understanding

**mem-weaver** is a local-first dual-LLM system inspired by Karpathy's LLM-wiki and Agent Skills taxonomy ([[agent-skills-taxonomy]]):

1. **Phase A (sync):** classify question → retrieve compiled wiki summary → LLM answers with summary as context
2. **Phase B (async):** Ollama incrementally merges Q+A into wiki pages after the user gets an answer

**Architecture** ([[mem-weaver-architecture]]): FastAPI middleware delegator, SQLite + FTS5 + sqlite-vec hybrid search (RRF), Obsidian-compatible Markdown vault, shared `memory_api` layer.

**As-built status** ([[mem-weaver-as-built-status]]): Codebase audit (2026-05-24) confirms Milestones A/B, Phase 4 hardening, hybrid search, `POST /chat` (SSE), and MCP server are **implemented**. Remaining wiring gaps: value gate, `_index.md` format alignment, optional hosted cloud LLM client.

**Known gaps** ([[mem-weaver-known-gaps]]): no episodic/semantic/procedural taxonomy, flat wikilink graph, no temporal validity on facts, no multi-tenant scoping. The chat frontend is now shipped; the remaining frontend work is polish and alignment with the wiki index flow.

**Release docs**: [CHANGELOG.md](../CHANGELOG.md), [docs/roadmap.md](roadmap.md), [docs/adr/](adr/)

## Chosen Approach

### Firm decisions

| Area | Choice | Wiki depth |
|------|--------|------------|
| Memory model | Synthesis-first wiki compilation + hybrid retrieval (FTS5 + sqlite-vec + RRF) | [[memory-synthesis-vs-rag]] |
| Pipeline shape | Dual-LLM: Ollama compiler (Phase B async) + LLM reasoner with wiki context (Phase A sync) | [[dual-llm-memory-pipeline]] |
| Ingest trigger | Per-turn async ingest on every Q+A (as built today) | [[dual-llm-memory-pipeline]] |
| Storage | SQLite index + Markdown vault + embeddings | [[mem-weaver-architecture]] |
| Topic routing | `SKILL_TAXONOMY` in classifier code (done) | [[agent-skills-taxonomy]] |
| IDE integration | stdio MCP server sharing `memory_api` with HTTP routes (done) | [[implementation-milestones]] |
| Wiki editing | Obsidian over `wiki/` — don't rebuild markdown admin | [[claude-frontend-admin-integration]] |

### Tentative / leaning

| Area | Lean | Notes |
|------|------|-------|
| Product positioning | OSS, local-first solo dev tool | Skip VC memory-startup path per [[claude-mem-weaver-competitive-analysis]] |
| Next UI priority | Either Next.js chat UI **or** MCP polish — both backends exist | See [[implementation-milestones]] divergence |
| Cloud LLM | Keep Ollama-only in `public_llm.py` until product requires Anthropic/OpenAI | [[mem-weaver-as-built-status]] |

### Next build (cross-cutting)

1. **Value gate** (`SKIP`/`PROCESS`) before summarize — [[mem-weaver-known-gaps]]
2. **Unify index format** — ingest writes `wiki/index.md`; chat retriever expects `_index.md` pipe-table — [[agent-skills-taxonomy]]
3. **Next.js chat frontend** — backend `/chat` exists; UI per [[claude-chat-app-frontend-design]]

## Constraints

- **Local-first / MacBook Pro:** Ollama runs locally; RAM limits model size for compiler role
- **API-based context control:** memory architecture depends on programmatic prompt assembly, not web chat auto-history ([[chatgpt-api-token-context-management]])
- **Single-user scope (today):** no auth, multi-tenant scoping, or enterprise compliance path
- **Summary quality bounded by local model:** Ollama compiler quality affects wiki fidelity; contradiction guardrails exist but value gate does not
- **Human-readable wiki:** Markdown vault is a product requirement — not a pure vector DB

## Non-Goals

- **VC-backed memory SaaS** competing with Mem0, Zep, Letta — positioning is personal/dev tool ([[claude-mem-weaver-competitive-analysis]])
- **Pure RAG without synthesis** — raw chunk retrieval alone rejected; compile-then-search hybrid chosen
- **Rebuilding Obsidian** for wiki browse/edit — use vault + plugins
- **Enterprise multi-tenant memory** in v1 — no auth/scoping API yet
- **Typed knowledge graph** in v1 — flat wikilinks only; graph layer is future ([[mem-weaver-known-gaps]])
- **Replacing parent project-wiki submodule** — this wiki tracks mem-weaver research; mem-weaver app code lives separately

## Rejected Alternatives

| Alternative | Why rejected | Source divergence |
|-------------|--------------|-------------------|
| Raw chat history replay to cloud LLM | Noisy, expensive, degrades with length | [[chatgpt-retrieval-vs-synthesis]] vs [[dual-llm-memory-pipeline]] |
| Vector/RAG-only memory (no wiki compile) | Misses compounding synthesis; context bloat on raw chunks | [[memory-synthesis-vs-rag]] |
| Batch-only wiki updates (3–5 turns) | Higher latency to fresh memory; per-turn async shipped first | [[claude-dual-llm-memory-pipeline]] vs as-built |
| ChromaDB / Neo4j as primary store | Codebase uses sqlite-vec + SQLite; simpler local stack | [[gemini-second-brain-design]] vs [[mem-weaver-architecture]] |
| MCP-only, no HTTP/chat paths | Both entry points valid; HTTP + MCP share `memory_api` | [[claude-mcp-server-design]] vs [[chatgpt-mem-weaver-v2-roadmap]] |
| Dynamic Ollama-invented topic categories (v1) | Harder to debug; fixed `SKILL_TAXONOMY` wired first | [[dual-llm-memory-pipeline]] divergence table |
| Hosted "public LLM" as default reasoner (today) | `public_llm.py` is Ollama-only; local-first preserved | [[mem-weaver-as-built-status]] |
| Custom Next.js markdown admin | Obsidian sufficient for editorial UX | [[claude-frontend-admin-integration]] |

## Open Questions

1. **Index format:** Teach ingest to write `_index.md` pipe-table, or retarget chat retriever to `wiki/index.md` + hybrid search? ([[agent-skills-taxonomy]])
2. **Entry point priority:** Ship Next.js chat UI next, or polish MCP/Cursor config for coding workflow? ([[implementation-milestones]])
3. **Cloud LLM:** Add Anthropic/OpenAI to `public_llm.py`, or stay Ollama-only? ([[mem-weaver-as-built-status]])
4. **Scale:** Is sqlite-vec sufficient long-term, or migrate to ChromaDB at vault size? ([[gemini-second-brain-design]])
5. **Memory taxonomy:** When to add episodic / semantic / procedural separation? ([[mem-weaver-known-gaps]])
6. **Product scope:** Remain solo dev + Obsidian tool, or expand toward SaaS (auth, scoping)? ([[claude-mem-weaver-competitive-analysis]])

---

For source attribution and evolving synthesis, drill into `wiki/concepts/` and [[evolving-thesis]]. Research continues — this brief is cycle 1 of an ongoing loop.
