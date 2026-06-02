---
type: synthesis
status: evolving
last_updated: 2026-05-29
sources_ingested: 28
---

# Evolving Research Thesis — mem-weaver

> Live synthesis synced from wiki/synthesis/evolving-thesis.md. Updated on every ingest.

## Current Understanding

**mem-weaver** is a local-first **dual-LLM memory system** for a MacBook Pro "second brain": a local Ollama model compiles Q+A exchanges into a persistent, searchable LLM-wiki (Karpathy pattern) organized with Agent Skills taxonomy, while chat answers use compiled wiki context instead of raw history.

### Core loop
1. **Phase A (sync):** User asks Q → delegator classifies topic → retrieves compiled wiki summary → LLM answers with summary as context (not raw history).
2. **Phase B (async):** After answer returns, Ollama incrementally merges Q+A into wiki pages.

### Architecture
- **FastAPI middleware delegator:** POST /ingest, GET /query, POST /chat (SSE), MCP stdio — all implemented.
- **Storage triad:** SQLite + Markdown vault + sqlite-vec embeddings. SQLite+FTS5 choice validated by NotebookLM.
- **Epistemic foundation:** LLM outputs are synthetic first-pass knowledge — wiki distillation is where verified signal emerges.

### Multi-LLM research workflow
Three independent LLM analyses converge on: Collect → Ingest → Synthesize → Export → Apply → Closed Loop.
- Context fragmentation is the root problem; context compression is the moat
- Contradictions tracking is where multi-LLM input earns its keep
- Human review gate is non-negotiable between wiki and implementation
- Two-stage ingestion: structural analysis → then generation and linkage

### Implementation progress
Milestones A/B, Phase 4 hardening, hybrid search, /chat (SSE), and MCP are done. Remaining: value gate, _index.md alignment, cloud LLM client.

### LLM Wiki paradigm
LLM Wiki moves knowledge synthesis from query phase (RAG) to ingestion phase. Each ingest permanently improves the knowledge asset. Three-layer architecture: Raw Sources → Wiki → Schema. Knowledge governance gaps (confidence, supersession, review queue) are the critical unaddressed risk.

### Known gaps
- No value gate in ingest pipeline
- _index.md vs wiki/index.md mismatch blocks chat retrieval
- No episodic/semantic/procedural memory taxonomy
- Flat wikilink graph; no temporal validity; no multi-tenant scoping
- Ollama-only — no hosted Anthropic/OpenAI client yet

## Open Questions
1. Index format: unify on _index.md or retarget chat retriever?
2. Entry point priority: Next.js chat UI or MCP polish?
3. Cloud LLM: add Anthropic/OpenAI or keep Ollama-only?
4. Vector store at scale: sqlite-vec sufficient or migrate?
5. Hallucination write-back: how to detect/prevent self-reinforcing errors?

## Emerging Decisions

| Decision | Status |
|----------|--------|
| Dual-LLM synthesis over raw history replay | **Decided** |
| Hybrid wiki compile + search retrieval | **Decided** |
| SKILL_TAXONOMY in classifier | **Decided** |
| MCP + shared memory_api | **Decided** |
| OSS/local-first; skip VC memory startup | **Leaning yes** |
| Value gate before summarize | **Next build** |
| Knowledge governance | **Open challenge** |
| Hallucination write-back detection | **Needs research** |
