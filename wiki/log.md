# Wiki log (append-only)

Chronological record per [Karpathy — LLM-Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) indexing guidance. Prefer grep-friendly prefixes.

## [2026-04-21] bootstrap | Initial LLM-wiki for REST

Seeded `wiki/index.md`, concept pages, and `LLM_WIKI_SCHEMA.md` to give agents and humans a stable map from Karpathy’s ingest/query/lint pattern to this repo’s FastAPI delegator (`server/main.py`). Pipeline persistence (raw JSON, SQLite, Ollama) not wired yet—see `docs/s2-claude-plan.md`.

## [2026-04-21] ingest | What is the capital of France?

Ingest `ing_20260421_85e7f6e2` → `wiki/concepts/geography.md`

## [2026-04-21] ingest | What is X?

Ingest `ing_20260421_da9cd993` → `wiki/concepts/what-is-x.md`
