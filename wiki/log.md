# Wiki log (append-only)

Chronological record per [Karpathy — LLM-Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) indexing guidance. Prefer grep-friendly prefixes.

## [2026-04-21] bootstrap | Initial LLM-wiki for REST

Seeded `wiki/index.md`, concept pages, and `LLM_WIKI_SCHEMA.md` to give agents and humans a stable map from Karpathy’s ingest/query/lint pattern to this repo’s FastAPI delegator (`server/main.py`). Pipeline persistence (raw JSON, SQLite, Ollama) not wired yet—see `docs/v2/s2-claude-plan.md`.

