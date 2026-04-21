-- SQLite + FTS5 (standalone FTS rows; app keeps pages + pages_fts in sync)

CREATE TABLE IF NOT EXISTS pages (
  id          TEXT PRIMARY KEY,
  title       TEXT NOT NULL,
  type        TEXT NOT NULL DEFAULT 'concept',
  path        TEXT NOT NULL UNIQUE,
  tags        TEXT,
  confidence  TEXT DEFAULT 'medium',
  created_at  TEXT NOT NULL,
  updated_at  TEXT NOT NULL,
  inbound_links INTEGER DEFAULT 0,
  content     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS qa_pairs (
  id          TEXT PRIMARY KEY,
  page_id     TEXT REFERENCES pages(id),
  question    TEXT NOT NULL,
  answer      TEXT NOT NULL,
  atom        TEXT NOT NULL,
  tags        TEXT,
  source      TEXT,
  session_id  TEXT,
  created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS wiki_links (
  from_page   TEXT NOT NULL,
  to_page     TEXT NOT NULL,
  PRIMARY KEY (from_page, to_page)
);

-- Standalone FTS: page_id links to pages.id (UNINDEXED = not tokenized)
CREATE VIRTUAL TABLE IF NOT EXISTS pages_fts USING fts5(
  page_id UNINDEXED,
  title,
  content,
  tags,
  tokenize = 'porter ascii'
);

CREATE VIRTUAL TABLE IF NOT EXISTS qa_fts USING fts5(
  qa_id UNINDEXED,
  question,
  answer,
  atom,
  tags,
  tokenize = 'porter ascii'
);
