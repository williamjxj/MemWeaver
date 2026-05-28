# Chat + Memory Workflow

MemWeaver’s core loop is not just chat and not just storage. It is a two-speed workflow:

- a fast user-facing answer path that uses the most relevant wiki context
- a slower background memory path that compiles new Q&A into durable knowledge

This note canonicalizes the shared ideas across the `v1`, `v2`, and `v3` drafts into one project-specific workflow.

## Source Drafts

- `docs/v1/s1-claude.md` - early dual-LLM memory pipeline with async wiki updates
- `docs/v1/s1-chatgpt.md` - retrieval vs. summarization comparison and the LLM-wiki pattern
- `docs/v2/s2-notebooklm.md` - multi-layer architecture with value gate, async compilation, and deterministic retrieval
- `docs/v2/s2-claude-plan.md` - stateless delegator, ingest pipeline, SQLite + Markdown store
- `docs/v3/deepseek.md` - local Ollama as memory compiler, public LLM as reasoning engine, wiki as persistent memory

## Canonical Workflow

1. The user asks a question in chat.
2. The chat endpoint retrieves the most relevant wiki context for the topic.
3. The public LLM answers using that small, pre-filtered context.
4. The raw Q&A pair is saved as an immutable record.
5. A background worker decides whether the turn is worth compounding into memory.
6. If the turn is valuable, the local LLM compiles the new facts into the wiki.
7. The wiki, index, and search structures are updated for later retrieval.
8. The next user question sees the improved memory, not the raw history.

## What This Means in MemWeaver

### Fast path

- Keep user latency low by answering before memory compilation finishes.
- Use deterministic retrieval first: wiki pages, index entries, tags, and search results.
- Avoid dumping the full conversation history into the prompt.

### Slow path

- Treat the local Ollama model as the memory compiler.
- Batch or gate updates when appropriate instead of rewriting memory on every low-value turn.
- Preserve previous versions when a summary changes materially.

### Storage model

- Raw Q&A belongs in immutable records.
- Durable knowledge belongs in human-readable wiki pages.
- Search indexes and graph links exist to make the wiki easy to navigate, not to replace it.

## Stable Design Rules

- Separate read latency from write latency.
- Prefer compact wiki summaries over raw turn history.
- Keep source drafts and canonical memory distinct.
- Use the wiki as the long-term memory surface, not the chat transcript.
- Make the background compiler incremental so the memory improves over time.

## Avoid

- Do not make the user wait for memory compilation before returning an answer.
- Do not rely on the full chat log as the primary long-term memory.
- Do not let multiple draft versions drift without a canonical note that captures the current rule.

## Relationship to the Codebase

This workflow matches the current repo shape:

- `server/` handles ingest, query, and chat orchestration.
- `wiki/` stores the compiled knowledge base.
- `raw/` stores immutable ingest artifacts.
- `db/` and FTS-backed search make retrieval deterministic and fast.
- `chat-app/` is the user-facing entry point that should surface the relevant memory without exposing the raw pipeline.

## Open Questions

- What is the right value gate for deciding whether a Q&A pair should be compiled?
- Should all turns be compiled asynchronously, or only turns that introduce new facts or decisions?
- How much memory version history should we keep for debugging and rollback?
- Which retrieval ranking should win when wiki text, topic tags, and graph links disagree?
