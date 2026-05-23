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
