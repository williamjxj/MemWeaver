---
id: karpathy-pattern-and-this-repo
title: "Karpathy LLM-Wiki pattern and this repository"
type: concept
tags: [llm-wiki, architecture, karpathy]
confidence: high
created: 2026-04-21
updated: 2026-04-21
---

# Karpathy LLM-Wiki pattern and this repository

[Andrej Karpathy’s LLM Wiki gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) describes a **compounding** knowledge base: the LLM incrementally maintains interlinked markdown (the wiki) using immutable **raw** sources and a **schema** that defines workflows.

This repository instantiates the **middleware delegator** slice: a **REST API** that chat clients call so ingest and query can be automated without Obsidian-open workflows only. The same three conceptual operations apply:

1. **Ingest** — new Q/A or source material enters the system; eventually summarized and merged into wiki pages and indexes (see [[rest-api-middleware-delegator]]).
2. **Query** — deterministic retrieval over compiled artifacts (FTS / index) plus optional LLM synthesis (s2 plan).
3. **Lint** — periodic consistency pass; here, primarily **agent-driven** until a route or tool exists.

Related: [[notebooklm-value-gate-bridge]] for async “memory manager” vs cloud “reasoning engine” split.
