# Wiki index — mem-wiki / LLM-Wiki delegator

Catalog of compiled pages. Updated when concepts change or new pages are added.

## Concepts

| Page | Summary |
|------|---------|
| [[karpathy-pattern-and-this-repo]] | How Karpathy’s LLM-Wiki gist maps onto this middleware. |
| [[rest-api-middleware-delegator]] | HTTP API: ingest, query, health (current vs planned). |
| [[notebooklm-value-gate-bridge]] | Value gate, async ingest, deterministic retrieval (s2-notebooklm). |

## External references

- [Karpathy — LLM Wiki (gist)](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
- `docs/v2/s2-claude-plan.md` — SQLite, FTS5, Ollama, directory layout
- `docs/v2/s2-notebooklm.md` — refined workflow and Agent Skills / markdown tiers

## Schema for agents

- [`LLM_WIKI_SCHEMA.md`](LLM_WIKI_SCHEMA.md) — rules for ingest/query/lint and REST usage

## Auto-index (pipeline)

- [[who-are-you]] — Hello! I'm **Qwen3.5**, the latest large language model developed by **Tongyi Lab**. I'm designed to assist with a wide range of tasks, including answering ques…
- [[read-and-analyse-the-following-and-translate-into-chinese-heres-]] — 这里是完整的专家分析： --- **① MemWeaver — MCP 与提示词框架 (Prompt Harness)** 你的提示词框架已经相当稳固（已具备 `.cursorrules`、`CLAUDE.md`、`AGENTS.md`）。真正的差距在于：**加入 MCP 服务器**。 你的 `/query`、`/in…
- [[what-is-rag]] — RAG stands for **Retrieval-Augmented Generation**. It's a technique used in artificial intelligence, particularly with large language models (LLMs), to improve …
- [[what-is-harness-engineering-does-hermes-agent-a-kind-of-harness-]] — There is some confusion here because both terms sound similar but usually refer to **completely different fields** or are non-standard phrases. Here is the brea…
- [[why-does-the-pipeline-use-rrf-for-hybrid-search]] — RRF (Reciprocal Rank Fusion) is a popular choice for hybrid search because it effectively combines ranked results from multiple retrieval sources, such as BM25 …
- [[what-obsidian-plugins-are-helpful-for-llm-wiki-purpose]] — When building an **LLM Wiki** in Obsidian (a second brain / knowledge base driven by AI), you need a specific set of plugins that facilitate **Retrieval Augment…
- [[mem0-vs-teammem]] — It appears there might be a slight confusion in the naming of the second product. **"mem0"** (by mem0.ai) is a well-known open-source memory management layer fo…
- [[memory-management]] — text2mem, mem0, and memweaver are terms possibly related to memory or data management systems.
- [[vector-databases]] — Vector databases store and query vectors for efficient retrieval in large language model applications.
- [[term]] — text2mem, mem0, and crew.ai are mentioned as potentially distinct terms or technologies.
