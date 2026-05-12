-- Semantic search: vec0 virtual table for nomic-embed-text (768-d) page embeddings
-- Requires sqlite-vec loadable extension (loaded at app startup).
-- page_id references pages.id; embedding is a serialized float32[768] BLOB.

CREATE VIRTUAL TABLE IF NOT EXISTS page_embeddings USING vec0(
  page_id TEXT PRIMARY KEY,
  embedding float[768]
);
