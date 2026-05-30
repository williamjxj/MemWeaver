---
type: project-details
status: current
date: 2026-05-29
export_cycle: 2
sources_ingested: 28
paired_brief: PROJECT_BRIEF.md
---

# Project Details: mem-weaver

> Deep analysis for export cycle 2. Companion to PROJECT_BRIEF.md. Synced from wiki/synthesis/project-details.md.

## Source Map

28 sources across 6 providers:

| Provider | Sources | Role |
|----------|---------|------|
| Claude | 16 | Primary architecture, plans, as-built audit |
| ChatGPT | 5 | Market positioning, v2 roadmap, workflow analysis |
| Gemini | 3 | Value gate, two-stage ingestion, closed-loop |
| NotebookLM | 1 | Independent architecture validation |
| YouTube (TGLTommy) | 1 (web) | LLM Wiki paradigm, knowledge governance |
| Claude pipeline plan | 1 | Pipeline operator, Open WebUI |

## Architecture (as implemented)

```
User / Client (Next.js UI / MCP / API)
    │
FastAPI Middleware Delegator
  POST /ingest (202) │ GET /query │ POST /chat │ MCP stdio
    │
┌──┴──────────────┐
Ollama Compiler   Hybrid Retriever
(Phase B async)   (FTS5 + sqlite-vec + RRF)
    │                      │
    └──────┬───────────────┘
           ▼
Storage Triad: SQLite + Markdown vault + sqlite-vec
```

## Comparison Matrix

| Topic | Claude | ChatGPT | Gemini | NotebookLM |
|-------|--------|---------|--------|------------|
| Pipeline | Dual-LLM Phase A/B | Dual-LLM, retrieval economy | Value gate + incremental | 3-phase roadmap |
| Storage | SQLite + Karpathy | Vector search or tags | Hierarchical + index | SQLite+FTS5 over ChromaDB |
| Taxonomy | _index.md + SKILL_TAXONOMY | Semantic search | Keyword scan + Ollama | Agent Skills |
| Human role | Non-negotiable gate | Less explicit gate | Obsidian review | N/A |

## Key Insights

### The paradigm shift: synthesis-at-ingest
Moving knowledge synthesis from query time (RAG) to ingestion time. Each ingest permanently improves the knowledge asset. The critical risk is hallucination write-back: LLM-written errors that later get retrieved as context, creating a self-reinforcing loop.

### Multi-LLM convergence
Five independent sources converge on the same pattern. Divergences are about emphasis, not architecture. The 2:1 resolution on LLM-Wiki vs "context engine" confirms the Karpathy pattern.

### What's built vs what's design
Built: all API endpoints, SQLite+FTS5+vec hybrid search, contradiction guardrails, DLQ, POST /chat (SSE), MCP server. Missing: value gate, index format alignment, cloud LLM client, knowledge governance.

## Recommendations

**Short-term:** Fix _index.md alignment; add value gate; document decision records.
**Medium-term:** Design knowledge governance; add purpose.md; evaluate pipeline operator.
**Longer-term:** Implement closed-loop harvesting; evolve flat wikilinks to typed graph.

## Risks
- Hallucination write-back (med likelihood, critical impact) — governance design before wiki scales
- Wiki maintenance overhead (med/med) — lint every 3-5 ingests
- Multi-LLM contradictions amplify errors (low/high) — human review resolves before export
