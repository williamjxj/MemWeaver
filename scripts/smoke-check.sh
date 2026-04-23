#!/usr/bin/env bash
# HTTP smoke checks against a running delegator (uvicorn).
# Prerequisite: server up, e.g. `uvicorn server.main:app --reload`
# Usage: ./scripts/smoke-check.sh
#        BASE_URL=http://127.0.0.1:9000 ./scripts/smoke-check.sh

set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
BASE_URL="${BASE_URL%/}"

tmp=""
cleanup() {
  if [[ -n "${tmp}" && -f "${tmp}" ]]; then
    rm -f "${tmp}"
  fi
}
trap cleanup EXIT

echo "Smoke check against ${BASE_URL}"
echo ""

echo "==> GET /health"
curl -sS -f "${BASE_URL}/health" | python3 -m json.tool 2>/dev/null || curl -sS -f "${BASE_URL}/health"
echo ""

echo "==> GET /stats"
curl -sS -f "${BASE_URL}/stats" | python3 -m json.tool 2>/dev/null || curl -sS -f "${BASE_URL}/stats"
echo ""

echo "==> GET /query?q=hello&limit=3"
curl -sS -f "${BASE_URL}/query?q=hello&limit=3" | python3 -m json.tool 2>/dev/null || curl -sS -f "${BASE_URL}/query?q=hello&limit=3"
echo ""

echo "==> POST /ingest (expect HTTP 202)"
tmp="$(mktemp)"
code="$(
  curl -sS -o "${tmp}" -w "%{http_code}" -X POST "${BASE_URL}/ingest" \
    -H "Content-Type: application/json" \
    -d "{\"question\":\"Smoke question?\",\"answer\":\"Smoke answer for CI.\",\"source\":\"smoke-check\"}"
)"
if [[ "${code}" != "202" ]]; then
  echo "FAIL: expected HTTP 202, got ${code}" >&2
  cat "${tmp}" >&2
  exit 1
fi
echo "HTTP ${code}"
cat "${tmp}" | python3 -m json.tool 2>/dev/null || cat "${tmp}"
echo ""

echo "==> GET /query?q=smoke&limit=5 (may be empty until worker finishes)"
curl -sS -f "${BASE_URL}/query?q=smoke&limit=5" | python3 -m json.tool 2>/dev/null || curl -sS -f "${BASE_URL}/query?q=smoke&limit=5"
echo ""

echo "All smoke checks passed."
