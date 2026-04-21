---
id: notebooklm-value-gate-bridge
title: "NotebookLM-style gate and async delegator"
type: concept
tags: [ollama, async, retrieval, s2-notebooklm]
confidence: medium
created: 2026-04-21
updated: 2026-04-21
---

# NotebookLM-style gate and async delegator

`docs/s2-notebooklm.md` refines the Karpathy pattern for a **Mac second brain**: public LLM for answers, **Ollama** locally as a memory compiler, FastAPI as delegator, markdown + optional vector/graph indices.

## Principles tied to REST

1. **Separate read/write latency** — `POST /ingest` should return quickly (`202`) while summarization and wiki writes run asynchronously (s2 §2.1 vs Phase A/B in s2-notebooklm).
2. **Value gate** — before expensive writes, a small local model may label `SKIP` vs `PROCESS` (s2-notebooklm §Phase B); that logic lives in the pipeline, not in the chat client.
3. **Deterministic retrieval** — `GET /query` should prefer SQLite FTS / structured index before asking an LLM to “find” pages across hundreds of files (aligns with gist comments on `index.md` scale limits).

## Links

- [[rest-api-middleware-delegator]] — HTTP entrypoints
- [[karpathy-pattern-and-this-repo]] — gist mapping
- `docs/s2-notebooklm.md` — full narrative
