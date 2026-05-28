# Ingest + Retrieval Pipeline

MemWeaver’s knowledge pipeline has one job: turn raw Q&A into durable wiki pages, then retrieve those pages quickly when the next question arrives.

This note canonicalizes the overlapping pipeline ideas from the `v2` and `v3` drafts and maps them to the current implementation in `server/`.

## Source Drafts

- `docs/v2/s2-claude-plan.md` - stateless delegator, async ingest, SQLite + Markdown storage, keyword query path
- `docs/v2/s2-notebooklm.md` - value gate, deterministic retrieval, background memory compilation
- `docs/v3/deepseek.md` - two-phase workflow, local compiler, public reasoning engine, wiki growth loop

## Current Pipeline

### Ingest path

1. `POST /ingest` accepts a Q&A pair.
2. The request is validated and queued immediately.
3. A background worker summarizes the Q&A into structured knowledge.
4. The raw payload is written to `raw/qa/<date>/<id>.json`.
5. The wiki page is created or updated under `wiki/concepts/`.
6. SQLite tables and FTS indexes are updated.
7. Wikilinks and index files are refreshed.
8. Failures go to the dead-letter queue.

### Retrieval path

1. `GET /query?q=...` searches the wiki index.
2. FTS5 returns ranked keyword matches.
3. Hybrid mode merges FTS and vector search with RRF.
4. Optional synthesis uses Ollama over the top snippets.
5. `GET /chat` retrieves a small wiki context first, then answers with the public LLM.

## What the Code Does Today

- [server/main.py](../../server/main.py) exposes `/ingest`, `/query`, `/chat`, `/health`, `/stats`, and `/wiki/{slug}`.
- [server/pipeline/ingest_worker.py](../../server/pipeline/ingest_worker.py) runs the async ingest pipeline.
- [server/pipeline/query_search.py](../../server/pipeline/query_search.py) handles FTS, hybrid search, and optional query-time synthesis.
- [server/services/classifier.py](../../server/services/classifier.py) and [server/services/wiki_retriever.py](../../server/services/wiki_retriever.py) route the chat context lookup.
- [server/pipeline/embedder.py](../../server/pipeline/embedder.py) and [server/pipeline/search_semantic.py](../../server/pipeline/search_semantic.py) support vector search.

## Canonical Rules

- Keep the ingest path asynchronous so the caller is never blocked by wiki compilation.
- Keep raw Q&A immutable and separate from the wiki output.
- Prefer deterministic retrieval before LLM synthesis.
- Use the wiki as the long-term memory surface, not the raw conversation log.
- Keep search, graph links, and embeddings as helpers around the wiki, not replacements for it.

## Retrieval Modes

- **Keyword**: FTS5 BM25 over the wiki index.
- **Semantic**: vector cosine search over stored embeddings.
- **Hybrid**: Reciprocal Rank Fusion over both result sets.

The current implementation already supports all three through the query API.

## Chat Loop

The chat route combines retrieval and generation:

1. classify the question into a topic
2. retrieve the smallest relevant wiki context
3. answer with the public LLM using that context
4. enqueue background compilation of the new turn

That keeps response latency low while still compounding memory over time.

## Operational Guidelines

- Do not make retrieval depend on the full chat history.
- Do not force memory compilation onto the critical path.
- Do not let source drafts define the implementation when the code already has a better source of truth.
- Do keep the wiki, raw store, and index in sync.

## Open Questions

- What threshold should a turn cross before it is worth compiling into the wiki?
- Should the value gate live in classification, summarization, or both?
- Which result type should win when keyword, semantic, and chat-context routing disagree?
- How much version history should be retained for wiki pages that change frequently?
