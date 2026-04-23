# Phase 4 — Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the six Phase 4 items from `docs/s2-claude-plan.md` §9: contradiction guardrails on wiki updates, `wiki_links` graph maintenance with correct `inbound_links`, real `orphan_pages` and `top_tags` on `/stats`, a file-based dead-letter queue for failed ingests, and automated tests (unit + one POST→GET integration path).

**Architecture:** Keep orchestration in `ingest_worker.py` but extract focused helpers: (1) pure `[[wikilink]]` parsing + DB sync in a small module, (2) optional post-generation contradiction pass via Ollama JSON before writing markdown, (3) DLQ writer invoked only from the worker `except` path, (4) stats queries as plain SQL in `main.py` or a thin `server/db/stats_queries.py`. Recompute `inbound_links` with a single SQL `UPDATE` after each ingest’s link sync so counts stay consistent without per-row application logic.

**Tech Stack:** Python 3.12, FastAPI, aiosqlite, httpx, pytest, pytest-asyncio (new dev dependencies).

---

## File Structure

| Path | Responsibility |
|------|----------------|
| `requirements.txt` | Add `pytest>=8,<9` and `pytest-asyncio>=0.24,<1` for CI/local runs. |
| `server/config/settings.py` | New `dlq_dir: Path` (default `raw/failed`), ensure parent dirs exist when writing DLQ. |
| `server/pipeline/prompts.py` | Add `CONTRADICTION_CHECK_PROMPT` (JSON out: `contradicts`, `note`). |
| `server/pipeline/wiki_graph.py` | **Create:** parse `[[...]]` links from markdown, `sync_outbound_links(db, from_page_id, markdown)`, `recompute_inbound_counts(db)`. |
| `server/pipeline/contradictions.py` | **Create:** `async def maybe_prepend_contradiction_block(settings, existing_body, atom, key_claims, draft_body) -> str` — calls Ollama only when `existing_body.strip()` non-empty; on failure returns `draft_body` unchanged. |
| `server/pipeline/ingest_worker.py` | Call contradiction helper after wiki LLM, before `write_text`; call `wiki_graph` after DB page upsert; wrap `run_ingest_pipeline` failures with DLQ write in `ingest_worker_loop`. |
| `server/main.py` | Extend `stats()` with SQL for `top_tags` and `orphan_pages`. |
| `tests/test_textutil.py` | Unit tests for `slugify` / `one_line`. |
| `tests/test_fts_match_terms.py` | Unit tests for `fts_match_terms`. |
| `tests/test_wiki_graph.py` | Unit tests for wikilink regex (no DB). |
| `tests/test_ingest_integration.py` | Async integration: mock Ollama + run `run_ingest_pipeline` or HTTP `lifespan` + `POST /ingest` + poll DB / `GET /query`. |

---

### Task 1: Add test dependencies

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Append dev dependencies**

Add these lines at the end of `requirements.txt`:

```text
pytest>=8,<9
pytest-asyncio>=0.24,<1
```

- [ ] **Step 2: Install and sanity check**

Run:

```bash
python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt && pytest --version
```

Expected: `pytest` prints a version (8.x).

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "chore: add pytest and pytest-asyncio for Phase 4 tests"
```

---

### Task 2: Unit tests for `textutil` and `fts_match_terms`

**Files:**
- Create: `tests/conftest.py`
- Create: `tests/test_textutil.py`
- Create: `tests/test_fts_match_terms.py`

- [ ] **Step 1: Create `tests/conftest.py`**

```python
import pytest

pytest_plugins = ("pytest_asyncio",)
```

- [ ] **Step 2: Write failing tests in `tests/test_textutil.py`**

```python
from server.pipeline.textutil import one_line, slugify


def test_slugify_ascii():
    assert slugify("Hello World!") == "hello-world"


def test_one_line_truncates():
    long = "word " * 50
    out = one_line(long, max_len=20)
    assert len(out) <= 21
    assert "…" in out or len(out) <= 20
```

- [ ] **Step 3: Write tests in `tests/test_fts_match_terms.py`**

```python
import pytest

from server.db.database import fts_match_terms


def test_fts_match_terms_empty():
    assert fts_match_terms("") == '""'


def test_fts_match_terms_two_words():
    m = fts_match_terms('foo bar')
    assert "OR" in m
    assert '"foo"' in m
    assert '"bar"' in m


def test_fts_match_terms_escapes_quote():
    m = fts_match_terms('say "hi"')
    assert '""' in m
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_textutil.py tests/test_fts_match_terms.py -v`

Expected: PASS (6 tests if you split fts into 3 tests).

- [ ] **Step 5: Commit**

```bash
git add tests/conftest.py tests/test_textutil.py tests/test_fts_match_terms.py
git commit -m "test: cover textutil and fts_match_terms"
```

---

### Task 3: `wiki_graph` — parse wikilinks and sync `wiki_links` + `inbound_links`

**Files:**
- Create: `server/pipeline/wiki_graph.py`
- Modify: `server/pipeline/ingest_worker.py` (call graph sync after page upsert, before or after `commit`; same transaction preferred)
- Modify: `server/pipeline/__init__.py` if you export symbols (optional)

- [ ] **Step 1: Write failing test for link extraction in `tests/test_wiki_graph.py`**

```python
import pytest

from server.pipeline.wiki_graph import extract_wikilink_targets


def test_extract_wikilinks_basic():
    md = "See [[transformers]] and [[attention-mechanism|Attention]]."
    assert extract_wikilink_targets(md) == ["transformers", "attention-mechanism"]


def test_extract_skips_empty():
    assert extract_wikilink_targets("no links") == []
```

Run: `pytest tests/test_wiki_graph.py -v`  
Expected: **FAIL** (`extract_wikilink_targets` not defined).

- [ ] **Step 2: Implement `server/pipeline/wiki_graph.py`**

```python
"""Wikilink extraction and `wiki_links` / inbound_counts maintenance."""

from __future__ import annotations

import re
from typing import Iterable

import aiosqlite

from server.pipeline.textutil import slugify

_WIKILINK = re.compile(r"\[\[([^\]|#]+)(?:\|[^\]]+)?\]\]")


def extract_wikilink_targets(markdown: str) -> list[str]:
    """Return target page ids: slugified Obsidian `[[target]]` / `[[target|alias]]` names."""
    seen: list[str] = []
    for m in _WIKILINK.finditer(markdown or ""):
        raw = m.group(1).strip()
        if not raw:
            continue
        tid = slugify(raw)
        if tid and tid not in seen:
            seen.append(tid)
    return seen


async def sync_outbound_links(
    db: aiosqlite.Connection,
    from_page_id: str,
    markdown: str,
) -> None:
    """Replace outbound edges from `from_page_id`, inserting only targets that exist as `pages.id`."""
    await db.execute("DELETE FROM wiki_links WHERE from_page = ?", (from_page_id,))
    for tid in extract_wikilink_targets(markdown):
        if tid == from_page_id:
            continue
        cur = await db.execute("SELECT 1 FROM pages WHERE id = ? LIMIT 1", (tid,))
        if await cur.fetchone():
            await db.execute(
                "INSERT OR IGNORE INTO wiki_links(from_page, to_page) VALUES (?, ?)",
                (from_page_id, tid),
            )


async def recompute_inbound_counts(db: aiosqlite.Connection) -> None:
    """Set `pages.inbound_links` from `wiki_links` indegree."""
    await db.execute(
        """
        UPDATE pages SET inbound_links = (
            SELECT COUNT(*) FROM wiki_links w WHERE w.to_page = pages.id
        )
        """
    )
```

- [ ] **Step 3: Run unit tests**

Run: `pytest tests/test_wiki_graph.py -v`  
Expected: PASS.

- [ ] **Step 4: Wire into `run_ingest_pipeline` in `ingest_worker.py`**

After the existing `qa_fts` insert block and **before** `await db.commit()`, add:

```python
        from server.pipeline import wiki_graph

        await wiki_graph.sync_outbound_links(db, page_id, full_md)
        await wiki_graph.recompute_inbound_counts(db)
```

Imports: prefer a single top-level `from server.pipeline import wiki_graph` in `ingest_worker.py` rather than inside the function if style allows.

- [ ] **Step 5: Manual smoke**

Run server, POST one ingest whose wiki body contains `[[some-existing-slug]]`, then:

```bash
sqlite3 db/wiki.db "SELECT * FROM wiki_links;"
```

Expected: at least one row when the target slug exists.

- [ ] **Step 6: Commit**

```bash
git add server/pipeline/wiki_graph.py server/pipeline/ingest_worker.py tests/test_wiki_graph.py
git commit -m "feat: sync wiki_links and inbound_links on ingest"
```

---

### Task 4: Contradiction block (LLM check before write)

**Files:**
- Modify: `server/pipeline/prompts.py`
- Create: `server/pipeline/contradictions.py`
- Modify: `server/pipeline/ingest_worker.py`
- Create: `tests/test_contradictions.py`

- [ ] **Step 1: Add prompt to `prompts.py`**

```python
CONTRADICTION_CHECK_PROMPT = """\
You compare a NEW knowledge atom against an EXISTING wiki page body.
Reply with JSON only: {{"contradicts": true or false, "note": "short reason if true, else empty string"}}

Contradiction means the new atom cannot both be true together with prominent claims already stated on the page (not mere elaboration).

Existing page body (excerpt):
---
{existing_excerpt}
---

New atom:
{atom}

New key claims (JSON):
{key_claims_json}
"""
```

- [ ] **Step 2: Failing test `tests/test_contradictions.py`**

```python
import pytest

from server.pipeline import contradictions


@pytest.mark.asyncio
async def test_maybe_prepend_skips_when_empty_existing(monkeypatch):
    calls = []

    async def fake_json(*a, **k):
        calls.append(1)
        return {"contradicts": True, "note": "x"}

    monkeypatch.setattr("server.pipeline.contradictions.ollama_generate_json", fake_json)
    settings = object()
    out = await contradictions.maybe_prepend_contradiction_block(
        settings, "", "atom", [], "BODY"
    )
    assert out == "BODY"
    assert calls == []
```

Run: `pytest tests/test_contradictions.py -v`  
Expected: FAIL until module exists.

- [ ] **Step 3: Implement `server/pipeline/contradictions.py`**

```python
"""Optional LLM pass to prepend a contradiction warning to wiki draft body."""

from __future__ import annotations

import json
import logging
from typing import Any

from server.config import Settings
from server.ollama.client import ollama_generate_json
from server.pipeline.prompts import CONTRADICTION_CHECK_PROMPT

logger = logging.getLogger(__name__)


async def maybe_prepend_contradiction_block(
    settings: Settings,
    existing_body: str,
    atom: str,
    key_claims: list[str],
    draft_body: str,
) -> str:
    """If page already has content, ask Ollama whether the new atom contradicts it."""
    excerpt = (existing_body or "").strip()
    if len(excerpt) < 40:
        return draft_body
    try:
        data = await ollama_generate_json(
            settings.ollama_host,
            settings.ollama_model,
            CONTRADICTION_CHECK_PROMPT.format(
                existing_excerpt=excerpt[:6000],
                atom=atom,
                key_claims_json=json.dumps(key_claims, ensure_ascii=False),
            ),
            timeout=min(60.0, settings.ollama_timeout),
        )
    except Exception:
        logger.exception("contradiction check failed; using draft without prepend")
        return draft_body
    if not isinstance(data, dict) or not data.get("contradicts"):
        return draft_body
    note = str(data.get("note") or "Possible conflict with existing page.").strip()
    prefix = f"> ⚠️ Contradiction noted: {note}\n\n"
    return prefix + draft_body
```

- [ ] **Step 4: Call from `ingest_worker.py` after wiki LLM, before frontmatter merge**

Immediately after `wiki_body` is finalized (including the atom fallback branch), add:

```python
    wiki_body = await maybe_prepend_contradiction_block(
        settings, existing, atom, key_claims, wiki_body
    )
```

Use the same `existing` variable already computed from the prior page body (before the LLM wiki call).

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_contradictions.py -v`  
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add server/pipeline/prompts.py server/pipeline/contradictions.py server/pipeline/ingest_worker.py tests/test_contradictions.py
git commit -m "feat: optional LLM contradiction guard before wiki write"
```

---

### Task 5: Dead-letter queue for failed ingests

**Files:**
- Modify: `server/config/settings.py`
- Modify: `server/pipeline/ingest_worker.py`

- [ ] **Step 1: Add `dlq_dir` to settings**

```python
    dlq_dir: Path = Field(default=Path("raw/failed"))
```

- [ ] **Step 2: In `ingest_worker_loop`, on exception after `run_ingest_pipeline`**

```python
import traceback

# inside except Exception:
payload = {
    "ingest_id": job.ingest_id,
    "error": traceback.format_exc(),
    "job": {
        "question": job.question,
        "answer": job.answer,
        "source": job.source,
        "session_id": job.session_id,
        "tags": job.tags,
        "received_at": job.received_at.isoformat(),
    },
}
settings.dlq_dir.mkdir(parents=True, exist_ok=True)
path = settings.dlq_dir / f"{job.ingest_id}.json"
path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
```

- [ ] **Step 3: Test with forced failure**

Temporarily raise in `run_ingest_pipeline` or mock Ollama to fail; POST `/ingest`; confirm `raw/failed/ing_*.json` exists. Remove temporary raise before commit.

- [ ] **Step 4: Commit**

```bash
git add server/config/settings.py server/pipeline/ingest_worker.py
git commit -m "feat: write ingest failures to DLQ json under raw/failed"
```

---

### Task 6: `/stats` — `top_tags` and `orphan_pages`

**Files:**
- Modify: `server/main.py`

- [ ] **Step 1: Define orphan as zero inbound wikilinks**

In `stats()` after opening `db`, run:

```python
        cur = await db.execute(
            """
            SELECT COUNT(*) FROM pages p
            WHERE NOT EXISTS (
                SELECT 1 FROM wiki_links w WHERE w.to_page = p.id
            )
            """
        )
        orphan_pages = int((await cur.fetchone())[0])
```

- [ ] **Step 2: `top_tags` from flattened JSON tags on `qa_pairs`**

```python
        cur = await db.execute(
            """
            SELECT j.value AS tag, COUNT(*) AS c
            FROM qa_pairs
            CROSS JOIN json_each(qa_pairs.tags) AS j
            GROUP BY j.value
            ORDER BY c DESC
            LIMIT 15
            """
        )
        rows = await cur.fetchall()
        top_tags = [[str(r[0]), int(r[1])] for r in rows]
```

Handle empty DB: `top_tags` stays `[]`.

- [ ] **Step 3: Pass `orphan_pages` and `top_tags` into `StatsResponse`**

- [ ] **Step 4: Manual curl**

```bash
curl -sS http://127.0.0.1:8000/stats | python3 -m json.tool
```

Expected: `orphan_pages` is a non-negative integer; `top_tags` lists `[tag, count]` once ingests exist.

- [ ] **Step 5: Commit**

```bash
git add server/main.py
git commit -m "feat: compute top_tags and orphan_pages for stats"
```

---

### Task 7: Integration test — ingest then query (mocked Ollama)

**Files:**
- Create: `tests/test_ingest_integration.py`

- [ ] **Step 1: Implement test with monkeypatched Ollama**

Use a temporary `db_path` and `wiki_dir` under `tmp_path` fixture so tests do not touch the developer’s vault.

```python
import asyncio
from datetime import datetime, timezone

import pytest

from server.config import Settings
from server.db.database import init_db
from server.pipeline import query_search
from server.pipeline.ingest_worker import IngestJob, run_ingest_pipeline


@pytest.fixture
def isolated_settings(tmp_path):
    db = tmp_path / "t.db"
    wiki = tmp_path / "wiki"
    raw = tmp_path / "raw"
    s = Settings(
        db_path=db,
        wiki_dir=wiki,
        raw_dir=raw,
        ollama_host="http://127.0.0.1:9",
        ollama_model="test-model",
        ollama_timeout=5.0,
    )
    asyncio.run(init_db(s))
    return s


@pytest.mark.asyncio
async def test_ingest_then_query_roundtrip(isolated_settings, monkeypatch):
    settings = isolated_settings

    async def fake_json(host, model, prompt, timeout=120.0):
        return {
            "atom": "RAG combines retrieval with generation.",
            "key_claims": ["retrieval augments context"],
            "detected_topics": ["rag"],
            "detected_entities": [],
        }

    async def fake_text(host, model, prompt, timeout=120.0):
        return "## Summary\n\nRAG is retrieval-augmented generation.\n"

    monkeypatch.setattr(
        "server.pipeline.ingest_worker.ollama_generate_json", fake_json
    )
    monkeypatch.setattr(
        "server.pipeline.ingest_worker.ollama_generate_text", fake_text
    )
    job = IngestJob(
        ingest_id="ing_test_1",
        question="What is RAG?",
        answer="RAG uses a retriever plus an LLM.",
        source="test",
        session_id=None,
        tags=["nlp"],
        received_at=datetime.now(timezone.utc),
    )
    await run_ingest_pipeline(job, settings)

    rows = await query_search.search_pages(settings, "RAG", limit=5)
    assert len(rows) >= 1
    assert any("rag" in (r.get("path") or "").lower() for r in rows)
```

Adjust import paths if `contradictions` is not imported yet in `ingest_worker` (patch the module where `ollama_generate_json` is looked up — use the path `ingest_worker` uses for contradiction calls, or disable contradiction for this test by patching `maybe_prepend_contradiction_block` to identity).

- [ ] **Step 2: Run integration test**

Run: `pytest tests/test_ingest_integration.py -v`

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_ingest_integration.py
git commit -m "test: ingest to query roundtrip with mocked Ollama"
```

---

## Self-review

**1. Spec coverage (s2 §9 Phase 4):**

| Requirement | Task |
|-------------|------|
| Contradiction detection in wiki page update | Task 4 |
| Link graph (`wiki_links`) | Task 3 |
| Orphan page detection in `/stats` | Task 6 |
| Error handling + DLQ | Task 5 |
| Unit tests for pipeline steps | Tasks 2, 3, 4 |
| Integration POST → GET | Task 7 |

**2. Placeholder scan:** None intentional; integration test may need a one-line monkeypatch target fix if imports differ — adjust `monkeypatch.setattr` to the actual resolved symbol for `maybe_prepend_contradiction_block`.

**3. Type consistency:** `Settings` is constructed with explicit paths in tests; `IngestJob.received_at` must be timezone-aware `datetime` matching production.

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-22-phase-4-hardening.md`. Two execution options:

**1. Subagent-Driven (recommended)** — Dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach do you want?
