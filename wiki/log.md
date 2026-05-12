# Wiki log (append-only)

Chronological record per [Karpathy — LLM-Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) indexing guidance. Prefer grep-friendly prefixes.

## [2026-04-21] bootstrap | Initial LLM-wiki for REST

Seeded `wiki/index.md`, concept pages, and `LLM_WIKI_SCHEMA.md` to give agents and humans a stable map from Karpathy’s ingest/query/lint pattern to this repo’s FastAPI delegator (`server/main.py`). Pipeline persistence (raw JSON, SQLite, Ollama) not wired yet—see `docs/s2-claude-plan.md`.

## [2026-04-21] ingest | What is the capital of France?

Ingest `ing_20260421_85e7f6e2` → `wiki/concepts/geography.md`

## [2026-04-21] ingest | What is X?

Ingest `ing_20260421_da9cd993` → `wiki/concepts/what-is-x.md`

## [2026-04-23] ingest | Smoke question?

Ingest `ing_20260423_2103298b` → `wiki/concepts/smoke-testing.md`

## [2026-05-11] ingest | Smoke question?

Ingest `ing_20260511_50430203` → `wiki/concepts/smoke-question.md`

## [2026-05-11] feat | Semantic search with nomic-embed-text + sqlite-vec

Added hybrid search: FTS5 BM25 + vector cosine similarity merged via Reciprocal Rank Fusion.
- Embedder: `server/pipeline/embedder.py` — Ollama `/api/embeddings`, nomic-embed-text (768-d)
- Storage: `page_embeddings` vec0 table via `sqlite-vec` (migration `002_semantic_search.sql`)
- Vector search: `server/pipeline/search_semantic.py`
- Hybrid merge: `server/pipeline/query_search.py` — `search_hybrid()` with RRF (k=60)
- API: `GET /query?q=...&mode=keyword|semantic|hybrid`
- Tests: `tests/test_embedder.py`, `test_semantic_search.py`, `test_hybrid_search.py`
