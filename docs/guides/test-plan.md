# Test Plan — mem-weaver

> How to verify that the dual-LLM memory pipeline works correctly: chat, RAG, wiki,
> incremental prompts, and meaningful memory.

---

## 1. App Purpose (Why This Exists)

mem-weaver is a **local-first, dual-LLM memory pipeline**. It solves a specific problem:
LLM chat is stateless — every conversation either replays noisy raw history (token bloat,
"lost in the middle") or starts fresh (no compounding knowledge).

**The core loop:**

1. A user asks a question in chat.
2. The backend classifies the topic, retrieves the most relevant wiki page, and streams
   an answer from DeepSeek with that context injected.
3. After the answer, the user can **opt-in** to save the Q&A to memory.
4. If saved, Ollama distills the Q&A into a wiki page — silently, in the background.
5. Next time someone asks about the same topic, the wiki page is retrieved as context.
   Knowledge compounds. Context windows don't bloat.

The chat interface also has **two complementary query modes**: hybrid RAG (FTS5 + vector
search over the compiled wiki) and keyword wiki search. The three modes (QA Chat, RAG,
LLM-Wiki) share one pipeline but serve different retrieval depths.

---

## 2. Test Infrastructure

### Stack

| Layer | Tool | Purpose |
|-------|------|---------|
| Backend unit tests | `pytest` + `pytest-asyncio` | Python logic, streaming, DB ops |
| Backend integration | `TestClient` (FastAPI) | HTTP endpoint contracts |
| Backend smoke checks | `scripts/smoke-check.sh` | Live-server validation |
| Frontend | manual browser + `curl` | UI rendering, SSE streaming |

### Conventions (from existing tests)

- **Mocked Ollama**: Ingest test use `monkeypatch` to replace `ollama_generate_json` /
  `ollama_generate_text` with deterministic stubs — no real Ollama needed.
- **Isolated DB**: Integration tests use `tmp_path` fixtures and `init_db()` to create
  throwaway SQLite databases.
- **Monkeypatched classifier**: Chat tests replace `classify_topic` with a deterministic
  stub to avoid real topic classification.
- **TestClient for FastAPI**: Route-level tests use `TestClient(app)` with
  `monkeypatch`-ed dependencies.

### Running Tests

```bash
# All tests (requires venv)
./venv/bin/pytest tests/ -v

# Specific file
./venv/bin/pytest tests/test_ingest_integration.py -v

# With coverage
./venv/bin/pytest tests/ --cov=server -v

# Smoke check against running server
./scripts/smoke-check.sh
```

VSCode / Cursor: install the Python test plugin and run from the testing sidebar.

---

## 3. Unit Test Coverage (Existing)

| Test file | What it covers | Pattern |
|-----------|---------------|---------|
| `test_classifier.py` | Topic classification logic | Pure function tests |
| `test_deepseek_client.py` | SSE line parsing, `_extract_token`, `_DONE` sentinel | Mocked HTTP |
| `test_public_llm.py` | Message construction (`build_messages`), wiki template, history injection | Pure function |
| `test_chat_no_autosave.py` | `/chat` does NOT enqueue ingest after streaming | TestClient + monkeypatch |
| `test_ingest_integration.py` | Ingest → FTS5 query roundtrip | Isolated DB, mocked Ollama |
| `test_memory_api.py` | `enqueue_ingest`, `get_wiki_page`, `search_wiki` validation & errors | Isolated DB |
| `test_hybrid_search.py` | RRF formula correctness, hybrid search fallback to FTS5 | Isolated DB |
| `test_semantic_search.py` | Vector search, cosine similarity ranking | In-memory vec0 |
| `test_embedder.py` | Embedding generation, error handling | Mocked Ollama |
| `test_fts_match_terms.py` | FTS5 match term extraction | Isolated DB |
| `test_textutil.py` | Text utilities | Pure function |
| `test_contradictions.py` | Contradiction detection logic | Mocked Ollama |
| `test_wiki_graph.py` | Graph nodes/edges from DB | Isolated DB |
| `test_wiki_retriever.py` | Wiki summarization logic | Mocked Ollama |
| `test_mcp_server.py` | MCP tool calling (search, ingest, get_page, stats) | In-process test |
| `test_note_ingest.py` | `note` field persistence through ingest | Isolated DB |

---

## 4. End-to-End Test Scenarios

### 4.1 Chat — Basic SSE Streaming

**Purpose:** Verify the main chat flow works: topic classification → wiki context
retrieval → DeepSeek streaming → done event.

```bash
curl -N http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What is RAG in AI?"}'
```

**Expected output:**

```
event: token
data: {"text": "RAG"}

event: token
data: {"text": " stands for Retrieval-Augmented Generation..."}

event: done
data: {"wiki_slug": "rag", "topic": "ml", "context_chars": 512}
```

**Checklist:**
- [ ] First `event: token` arrives within 2 seconds (no long setup delay)
- [ ] Tokens arrive incrementally (not all at once)
- [ ] `event: done` fires with `wiki_slug` and `topic`
- [ ] No `event: error` is emitted
- [ ] Response status is `200`

### 4.2 Chat — Wiki Context Injection

**Purpose:** Verify that the retrieved wiki context changes the answer (vs. no context).

```bash
# First, ensure some wiki content exists via ingest
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"question": "What is RAG?", "answer": "RAG combines retrieval with generation.", "source": "test"}'

# Wait for ingestion (~10-30s), then chat
curl -N http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What is RAG?"}'
```

**Checklist:**
- [ ] `event: done` includes a non-empty `wiki_slug` (relevant page was found)
- [ ] `context_chars` is > 0 (context was injected)
- [ ] The answer references the previously ingested wiki content

### 4.3 Chat — No Auto-Save (Opt-In)

**Purpose:** Verify that chat does NOT automatically persist Q&A to the wiki.

```bash
# Chat without saving
curl -N http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Tell me about Python lists"}'

# Check stats — should show no new ingests
curl http://localhost:8000/stats
```

**Checklist:**
- [ ] Chat returns 200 with SSE events
- [ ] `GET /stats` shows no increase in `total_ingests`
- [ ] No wiki page was created for this chat turn

**Test:** `test_chat_no_autosave.py` covers this programmatically.

### 4.4 Chat — Save to Memory (Opt-In)

**Purpose:** Verify the frontend's explicit save flow persists Q&A.

```bash
# After a chat, the frontend sends:
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Tell me about Python lists",
    "answer": "Python lists are ordered, mutable collections...",
    "source": "chat",
    "note": "user opted to save",
    "tags": ["python", "data-structures"]
  }'
```

**Checklist:**
- [ ] Returns HTTP 202 with `ingest_id`
- [ ] After ~30s, `GET /query?q=python+lists&mode=keyword` returns the new page
- [ ] Raw JSON artifact exists at `raw/qa/<date>/<ingest_id>.json`
- [ ] Wiki markdown exists at `wiki/concepts/python-lists.md`
- [ ] The `note` field is present in the raw JSON

**Frontend flows:**
- Open `http://localhost:3000`, ask a question in the QA Chat panel
- When the answer completes, a "Save to memory" checkbox appears below the answer
- Check it, optionally add a note, click Save
- Verify: the QA Chat panel shows "Saved ✓" on success
- Verify: the RAG or Wiki panel can now find this content by searching

---

## 5. Search / RAG Tests

### 5.1 Keyword Search (FTS5 BM25)

**Purpose:** Exact-match retrieval — low latency, deterministic, zero Ollama cost.

```bash
curl "http://localhost:8000/query?q=rag&mode=keyword&limit=5"
```

**Checklist:**
- [ ] Response time < 100ms (no LLM call)
- [ ] Results contain pages with "rag" in title, content, or tags
- [ ] BM25 scores are negative; more negative = better match
- [ ] `total` reflects actual match count
- [ ] Omitting `mode` defaults to `hybrid`

### 5.2 Semantic Search (Vector Cosine Similarity)

**Purpose:** Conceptual matches — catches things keyword search misses.

```bash
curl "http://localhost:8000/query?q=how+do+models+weigh+token+relevance&mode=semantic&limit=5"
```

**Checklist:**
- [ ] Response returns results (may take 1-3s for Ollama embedding call)
- [ ] Returns conceptually related pages even if keywords don't match
- [ ] Scores are positive; lower = more similar
- [ ] If no `page_embeddings` exist, returns empty results (not an error)

### 5.3 Hybrid Search (RRF Merge)

**Purpose:** Best of both — keyword precision + semantic breadth.

```bash
curl "http://localhost:8000/query?q=attention+mechanism&mode=hybrid&limit=5"
```

**Checklist:**
- [ ] Results include both keyword-matched AND conceptually-matched pages
- [ ] Pages that match in both channels rank higher (RRF boost)
- [ ] RRF constant is 60 (verify in code)
- [ ] `limit` parameter is respected (1-50)

### 5.4 Summarized Answer

**Purpose:** Optional post-processing that synthesizes snippets into a paragraph.

```bash
curl "http://localhost:8000/query?q=rag&summarize=true&limit=3"
```

**Checklist:**
- [ ] Response includes `summarized_answer` string (non-null)
- [ ] The summary is a coherent paragraph, not just a snippet
- [ ] `summarize=true` is noticeably slower (calls Ollama over snippets)

### 5.5 Search Edge Cases

```bash
# Empty query → 400
curl -s "http://localhost:8000/query?q="

# Very short query
curl -s "http://localhost:8000/query?q=a"

# Special characters
curl -s "http://localhost:8000/query?q=FTS5+BM25+%26+sqlite-vec"

# Limit boundary
curl -s "http://localhost:8000/query?q=rag&limit=1"
curl -s "http://localhost:8000/query?q=rag&limit=50"

# Invalid mode
curl -s "http://localhost:8000/query?q=rag&mode=invalid"
```

**Checklist:**
- [ ] Empty query returns 400 with error message
- [ ] Single-char query works (FTS5 handles short strings)
- [ ] Special characters are URL-encoded properly
- [ ] `limit=1` returns exactly 1 result
- [ ] `limit=50` returns at most 50 (or fewer)
- [ ] Invalid mode returns validation error (422)

---

## 6. Wiki Tests

### 6.1 Wiki Page Retrieval

```bash
# Workspace query
curl "http://localhost:8000/wiki/geo%20-%20geography"

# Direct slug
curl "http://localhost:8000/wiki/concepts/rag"

# Non-existent page
curl "http://localhost:8000/wiki/nonexistent-page"
```

**Checklist:**
- [ ] Existing pages return `{"slug": "...", "content": "..."}` with markdown body
- [ ] Non-existent pages return empty `content` (not 404)
- [ ] URL-encoded slashes work (`%20` for spaces)
- [ ] Content includes frontmatter (if present)

### 6.2 Wiki Graph

```bash
curl "http://localhost:8000/wiki/graph"
```

**Checklist:**
- [ ] Returns `{"nodes": [...], "edges": [...]}`
- [ ] Each node has `id`, `title`, `category`, `inbound_links`
- [ ] Each edge has `source` and `target`
- [ ] Works with no data (returns empty arrays, not error)
- [ ] Frontend: the graph widget in the dashboard renders nodes and edges
- [ ] Frontend: clicking a node navigates to the wiki page

### 6.3 Wiki Tree

```bash
curl "http://localhost:8000/wiki/tree"
```

**Checklist:**
- [ ] Returns `{"tree": [...]}` with `folder` entries containing `children`
- [ ] Concepts section populated from `wiki/index.md`
- [ ] Auto-index section populated (if present)
- [ ] Works when `wiki/index.md` doesn't exist (returns empty tree)
- [ ] Frontend: sidebar displays the tree correctly

---

## 7. Ingest Pipeline Tests

### 7.1 Basic Ingest

```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"question": "What is a transformer?", "answer": "A transformer uses self-attention.", "source": "test"}'
```

**Checklist:**
- [ ] Returns HTTP 202 with `ingest_id` and `queued_at`
- [ ] Poll `GET /stats`: `total_ingests` and `total_wiki_pages` increase after ~30s
- [ ] Raw JSON at `raw/qa/<date>/<id>.json` contains the Q&A
- [ ] Wiki page at `wiki/concepts/transformer.md` exists
- [ ] Query works: `GET /query?q=transformer&mode=keyword` returns the page
- [ ] Semantic search works: `GET /query?q=self-attention&mode=semantic` returns it

### 7.2 Ingest with Note

```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is FastAPI?",
    "answer": "FastAPI is a modern Python web framework.",
    "source": "chat",
    "note": "user-initiated save",
    "tags": ["python", "web"]
  }'
```

**Checklist:**
- [ ] `raw/qa/<date>/<id>.json` contains a `note` field
- [ ] `note` value matches what was sent
- [ ] Tags appear in `GET /stats` top_tags

**Test:** `test_note_ingest.py` covers this.

### 7.3 Ingest Validation

```bash
# Empty question
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"question": "", "answer": "something"}'

# Missing question
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"answer": "something"}'

# Queue full (unlikely in dev, but test with many concurrent requests)
```

**Checklist:**
- [ ] Empty question returns 422 validation error
- [ ] Missing required fields return 422
- [ ] Error messages are descriptive

### 7.4 Concurrent Ingest & Queue Depth

```bash
# Submit 5 ingests in rapid succession
for i in $(seq 1 5); do
  curl -s -X POST http://localhost:8000/ingest \
    -H "Content-Type: application/json" \
    -d "{\"question\": \"Q $i?\", \"answer\": \"A $i.\", \"source\": \"stress\"}" &
done
wait
# Check stats
curl http://localhost:8000/stats
```

**Checklist:**
- [ ] All 5 return HTTP 202
- [ ] All 5 are eventually compiled (stats increase by 5)
- [ ] No 503 errors (unless queue is small)
- [ ] No data corruption (each page is distinct)

---

## 8. Incremental Prompt / Memory Compounding

**Purpose:** This is the app's core value proposition. Verify that over multiple
turns, the wiki accumulates knowledge and retrieval improves.

### 8.1 Multi-turn Chat with Same Topic

**Scenario:**
1. Ask "What are Python list comprehensions?" → chat answers via DeepSeek
2. Manually save the Q&A to memory (via the SaveToMemory UI or direct `/ingest`)
3. Wait for ingest to complete
4. Ask "How do I filter a list with a comprehension?" → should now retrieve the
   Python lists wiki page as context

**Detailed walkthrough:**

```bash
# Turn 1: Ask a question
# (through the chat UI or directly via curl to /chat)
# The answer streams back but is NOT auto-saved.

# Manually save what was learned
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are Python list comprehensions?",
    "answer": "List comprehensions provide a concise way to create lists...",
    "source": "chat-manual",
    "tags": ["python"]
  }'

# Wait ~30s for pipeline to finish
sleep 30

# Turn 2: Ask a related question
curl -N http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "How do I filter a list with a comprehension?"}'
```

**Checklist:**
- [ ] Turn 2 `event: done` includes `wiki_slug` referencing the Python concepts page
- [ ] The answer references content from turn 1's ingested Q&A
- [ ] `GET /stats` shows increased `wiki_pages` and `qa_pairs`

### 8.2 Cross-Topic Knowledge Separation

**Purpose:** Verify the wiki separates topics correctly (no bleed).

1. Ingest content about "Python" → saved to `wiki/concepts/python.md`
2. Ingest content about "JavaScript" → saved to `wiki/concepts/javascript.md`
3. Ask "What is a closure in JS?" → should retrieve JavaScript page, not Python
4. Ask "What is a list comprehension?" → should retrieve Python page, not JS

### 8.3 Search Quality Improvement Over Time

**Purpose:** Verify the wiki grows and search quality compounds.

1. Start with empty wiki
2. `GET /query?q=rag` → returns 0 results
3. Ingest a Q&A about RAG
4. Wait for pipeline
5. `GET /query?q=rag&mode=keyword` → returns 1 result
6. Ingest 5 more RAG-related Q&As
7. `GET /query?q=rag&mode=hybrid` → returns multiple results, better ranking
8. `GET /query?q=retrieval+generation&mode=semantic` → finds RAG pages even
   though the query doesn't contain "RAG" (conceptual match)

---

## 9. Frontend Testing (Manual)

### 9.1 Stage-Tab Navigation

Open `http://localhost:3000`. Verify:

- [ ] Landing on "Compare" view shows all three panels side by side
- [ ] Clicking "QA Chat" narrows to a single larger panel
- [ ] Clicking "RAG" shows the RAG panel
- [ ] Clicking "LLM-Wiki" shows the wiki panel
- [ ] Clicking "Compare" returns to the three-panel layout

### 9.2 QA Chat Panel

- [ ] Type a question and press Enter
- [ ] The response streams in token-by-token (words appear incrementally)
- [ ] Markdown in the response is rendered (bold, code blocks, lists)
- [ ] When streaming completes, a "Save to memory" checkbox appears
- [ ] Checking the box reveals an optional note textarea and Save button
- [ ] Clicking Save shows "Saved ✓" and the data is queryable via RAG/wiki

### 9.3 RAG Panel

- [ ] Type a query and press Send
- [ ] Results show synthesized answer + source snippets
- [ ] Clicking a source snippet navigates to the wiki page
- [ ] Empty state shows the placeholder text

### 9.4 LLM-Wiki Panel

- [ ] Type a keyword query and press Query
- [ ] Results are returned as wiki markdown snippets
- [ ] Works the same as `GET /query?mode=keyword`

### 9.5 Graph Widget

- [ ] Navigate to the Dashboard (Compare view)
- [ ] The graph widget shows nodes and edges
- [ ] Nodes are draggable
- [ ] Hovering shows a tooltip with the page title

### 9.6 Wiki Sidebar

- [ ] The right sidebar shows the wiki tree
- [ ] Clicking a concept loads the wiki page content
- [ ] The tree refreshes after new ingests

---

## 10. MCP Server Tests

```bash
# Start the MCP server standalone
python3 server/mcp_server.py

# Test via a direct JSON-RPC call (or through Cursor/Claude Code)
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"wiki_stats","arguments":{}}}' | nc -U /tmp/memweaver.sock
```

**Checklist:**
- [ ] `wiki_search` — returns search results, handles empty queries, handles missing DB
- [ ] `wiki_ingest` — returns 202-style response, validates input
- [ ] `wiki_get_page` — returns content, handles missing slugs
- [ ] `wiki_stats` — returns counters, handles missing DB
- [ ] MCP server starts without FastAPI running (standalone mode)
- [ ] MCP tools share the same `memory_api` service layer as HTTP routes

**Test:** `test_mcp_server.py` covers this programmatically.

---

## 11. Reliability & Edge Cases

### 11.1 Ollama Unreachable

- [ ] Health check: `GET /health` returns `ollama: "unreachable"` when Ollama is down
- [ ] Ingest pipeline doesn't crash the server when Ollama is unreachable
- [ ] Chat still works (DeepSeek is separate from Ollama)
- [ ] Keyword search still works (no Ollama dependency)

### 11.2 DeepSeek API Unavailable

- [ ] Chat returns error event when `DEEPSEEK_API_KEY` is not configured
- [ ] Ingest pipeline still works (uses Ollama, not DeepSeek)
- [ ] Search still works (no DeepSeek dependency)

### 11.3 Server Restart Resilience

- [ ] Wiki pages persist after server restart (they're files on disk)
- [ ] SQLite database persists (it's a file)
- [ ] Ingest queue is lost on restart (expected — it's in-memory `asyncio.Queue`)

### 11.4 Backfill Scripts

```bash
# Backfill embeddings for pages that have no vectors
python3 scripts/backfill_embeddings.py
```

- [ ] After running, all existing pages get vectors
- [ ] Semantic search works for previously-backfilled pages
- [ ] Idempotent — running twice is safe

```bash
# Backfill wikilinks for pages
python3 scripts/backfill_wikilinks.py
```

- [ ] Wikilinks are generated from `[[wikilink]]` syntax in existing pages
- [ ] `wiki_link` table is populated
- [ ] `inbound_links` counts are correct

---

## 12. Test Matrix (Quick Reference)

| Component | Unit test | Integration test | Smoke check | Manual QA |
|-----------|-----------|-----------------|-------------|-----------|
| Chat SSE streaming | ✓ | ✓ | ✓ | ✓ |
| Wiki context injection | ✓ | - | - | ✓ |
| No auto-save | ✓ | - | - | ✓ |
| Opt-in save | ✓ | ✓ | - | ✓ |
| Keyword search | ✓ | ✓ | ✓ | ✓ |
| Semantic search | ✓ | ✓ | - | ✓ |
| Hybrid search | ✓ | ✓ | - | ✓ |
| Search summarize | - | - | - | ✓ |
| Wiki page retrieval | ✓ | - | - | ✓ |
| Wiki graph | ✓ | ✓ | - | ✓ |
| Wiki tree | - | - | - | ✓ |
| Ingest pipeline | ✓ | ✓ | ✓ | ✓ |
| Ingest with note | ✓ | ✓ | - | ✓ |
| DeepSeek client | ✓ | - | - | - |
| MCP server | ✓ | - | - | ✓ |
| Frontend rendering | - | - | - | ✓ |

---

## 13. CI / Automation

For automated runs, use the smoke check script as a gate:

```bash
# Terminal 1: start server
uvicorn server.main:app --reload &
sleep 3

# Terminal 2: run smoke checks
./scripts/smoke-check.sh

# Run all unit tests
./venv/bin/pytest tests/ -v --tb=short
```

For full end-to-end validation (requires Ollama + DeepSeek key):

```bash
# 1. Server must be running with .env configured
# 2. Run smoke checks
./scripts/smoke-check.sh

# 3. Ingest a test Q&A
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"question":"Test plan question?","answer":"This is a test answer.","source":"test-plan"}'

# 4. Wait then search
sleep 30
curl "http://localhost:8000/query?q=test+plan&mode=hybrid"

# 5. Chat
curl -N http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"What was the test question I just ingested?"}'
```

---

## 14. Regression Checklist (Pre-Release)

Before tagging a release, run through:

- [ ] `./venv/bin/pytest tests/ -v` — all green
- [ ] `./scripts/smoke-check.sh` — all HTTP endpoints respond correctly
- [ ] Chat streams tokens and fires `event: done`
- [ ] Ingest returns 202 and the pipeline completes
- [ ] Keyword, semantic, and hybrid search all return results
- [ ] Wiki graph returns nodes + edges
- [ ] MCP server starts and responds to tool calls
- [ ] Frontend loads and all three panels work
- [ ] Save-to-memory checkbox appears and persists content
- [ ] No sensitive data (API keys) is leaked in responses or logs
