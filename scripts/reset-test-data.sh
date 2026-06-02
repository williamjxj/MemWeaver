#!/usr/bin/env bash
# Full reset for MemWeaver runtime data. Run from the repo root.
#
#   ./scripts/reset-test-data.sh
#
# Removes runtime artifacts and rewrites the wiki to a clean baseline so the
# app starts as if no ingests or chats have happened yet.

set -euo pipefail
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo "${0%/*}/..")"

shopt -s nullglob

echo "==> Removing raw ingest artifacts …"
rm -rf raw/qa/*/ raw/failed/*

echo "==> Removing generated wiki/concept pages …"
rm -f wiki/concepts/*.md

echo "==> Removing SQLite database …"
rm -fv db/wiki.db db/*.db

echo "==> Rebuilding wiki/index.md and wiki/log.md from scratch …"
cat > wiki/index.md <<'EOF'
# Wiki index — mem-wiki / LLM-Wiki delegator

Catalog of compiled pages. Updated when concepts change or new pages are added.

## Concepts

| Page | Summary |
|------|---------|

## External references

- [Karpathy — LLM Wiki (gist)](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
- `docs/s2-claude-plan.md` — SQLite, FTS5, Ollama, directory layout
- `docs/s2-notebooklm.md` — refined workflow and Agent Skills / markdown tiers

## Schema for agents

- [`LLM_WIKI_SCHEMA.md`](LLM_WIKI_SCHEMA.md) — rules for ingest/query/lint and REST usage

## Auto-index (pipeline)

EOF

cat > wiki/log.md <<'EOF'
# Wiki log (append-only)

Chronological record per [Karpathy — LLM-Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) indexing guidance. Prefer grep-friendly prefixes.
EOF

echo "==> Removing browser/app-local history if present …"
rm -f chat-app/.next/cache/* 2>/dev/null || true

echo ""
echo "Done. Restart uvicorn and refresh the browser to recreate the SQLite schema and clear in-memory UI state."
