#!/usr/bin/env bash
# Remove all pipeline-generated test/chat data while preserving hand-seeded
# wiki concept pages.  Run from the repo root.
#
#   ./scripts/reset-test-data.sh
#
# Removes:
#   raw/qa/*              — immutable ingest JSON files
#   wiki/concepts/*.md    — all generated pages (keeps 3 hand-seeded ones)
#   db/wiki.db            — SQLite database (recreated on next server start)
#   wiki/index.md auto-index entries
#   wiki/log.md ingest entries

set -euo pipefail
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo "${0%/*}/..")"

echo "==> Removing raw/qa ingest files …"
rm -rf raw/qa/*/

echo "==> Removing generated wiki/concept pages …"
for f in wiki/concepts/*.md; do
  case "${f##*/}" in
    karpathy-pattern-and-this-repo.md|rest-api-middleware-delegator.md|notebooklm-value-gate-bridge.md)
      echo "    keeping ${f##*/}"
      ;;
    *)
      rm -v "$f"
      ;;
  esac
done

echo "==> Removing SQLite database …"
rm -fv db/wiki.db

echo "==> Cleaning wiki/index.md (removing auto-index section) …"
awk '
  /^## Auto-index/ { skip = 1; next }
  skip && /^## /  { skip = 0 }  # stop skipping at next heading
  skip            { next }
  !skip           { print }
' wiki/index.md > wiki/index.md.tmp && mv wiki/index.md.tmp wiki/index.md

echo "==> Cleaning wiki/log.md (removing ingest entries after bootstrap) …"
awk '
  /^## \[2026-05/ || /^## \[2026-04-2[1-9]/ { next }
  /^Ingest /  { next }
  { print }
' wiki/log.md > wiki/log.md.tmp && mv wiki/log.md.tmp wiki/log.md
# Remove trailing blank lines left by awk filtering
sed -i '' -e :a -e '/^\n*$/{$d;N;ba}' wiki/log.md 2>/dev/null || true

echo ""
echo "Done. Restart uvicorn to recreate the SQLite schema on first request."
