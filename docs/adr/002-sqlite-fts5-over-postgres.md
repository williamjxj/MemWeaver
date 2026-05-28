# ADR 002: SQLite FTS5 Over Postgres

## Context
The project is a local-first wiki-memory system with a Markdown vault, a single ingest worker, and search that must be fast, deterministic, and easy to run without extra infrastructure. The current design needs full-text search, structured persistence, and later semantic indexing, but not a multi-user database service.

## Decision
Use SQLite as the primary database, with FTS5 for keyword search and `sqlite-vec` for semantic search. Keep the storage embedded in the repo’s runtime environment instead of introducing Postgres for the first production-shaped version of the system.

## Consequences
This keeps deployment simple: one app process, one local database file, and no separate database server to provision or back up. It also fits the current access pattern well because reads are mostly local and writes are serialized through the ingest queue. The downside is that SQLite is less suited than Postgres for high concurrency, multi-writer scaling, and advanced operational tooling, so a future migration would require deliberate schema and query work.
