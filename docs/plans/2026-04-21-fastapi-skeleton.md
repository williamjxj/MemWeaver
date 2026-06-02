# FastAPI Skeleton Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a runnable FastAPI skeleton with `POST /ingest`, `GET /query`, and `GET /health`, plus minimal README run instructions.

**Architecture:** Keep the milestone as a thin vertical slice with a single app file (`server/main.py`) and contract-shaped mock responses. Do not add persistence, queue workers, Ollama integration, or settings scaffolding in this phase.

**Tech Stack:** Python 3.12, FastAPI, Uvicorn

---

## File Structure

- Create: `server/main.py` — minimal FastAPI app and three routes.
- Create: `README.md` — minimal run and smoke-check instructions.
- No tests in this milestone by design (matches approved spec scope).

---

### Task 1: Create Server Skeleton Routes

**Files:**
- Create: `server/main.py`

- [ ] **Step 1: Create `server/main.py` with contract-shaped route handlers**

```python
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import Body, FastAPI, Query
from fastapi.responses import JSONResponse

app = FastAPI(title="LLM-Wiki Middleware Delegator")


@app.post("/ingest")
async def ingest(payload: dict = Body(default_factory=dict)) -> JSONResponse:
    _ = payload  # kept permissive by design in milestone A
    return JSONResponse(
        status_code=202,
        content={
            "status": "accepted",
            "ingest_id": f"ing_{uuid4().hex[:12]}",
            "queued_at": datetime.now(timezone.utc).isoformat(),
        },
    )


@app.get("/query")
async def query(
    q: str = Query(..., description="Search query"),
    limit: int = Query(5, ge=1),
) -> dict:
    _ = limit
    return {
        "query": q,
        "results": [],
        "total": 0,
        "summarized_answer": None,
    }


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
```

- [ ] **Step 2: Run the server**

Run: `uvicorn server.main:app --reload`

Expected output contains lines similar to:

```text
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

- [ ] **Step 3: Smoke-check `GET /health`**

Run: `curl -s http://127.0.0.1:8000/health`

Expected output:

```json
{"status":"ok"}
```

- [ ] **Step 4: Smoke-check `GET /query` happy path**

Run: `curl -s "http://127.0.0.1:8000/query?q=test&limit=3"`

Expected output:

```json
{"query":"test","results":[],"total":0,"summarized_answer":null}
```

- [ ] **Step 5: Smoke-check `GET /query` validation behavior**

Run: `curl -i "http://127.0.0.1:8000/query"`

Expected output contains:

```text
HTTP/1.1 422 Unprocessable Entity
```

- [ ] **Step 6: Smoke-check `POST /ingest` acceptance**

Run:

```bash
curl -s -X POST "http://127.0.0.1:8000/ingest" \
  -H "Content-Type: application/json" \
  -d '{"question":"What is RAG?","answer":"Retrieval-augmented generation."}'
```

Expected output shape:

```json
{"status":"accepted","ingest_id":"ing_xxxxxxxxxxxx","queued_at":"<iso-utc-time>"}
```

- [ ] **Step 7: Commit**

```bash
git add server/main.py
git commit -m "feat: add FastAPI skeleton routes for ingest query and health"
```

---

### Task 2: Add Minimal Run Instructions

**Files:**
- Create: `README.md`

- [ ] **Step 1: Create `README.md` with run and smoke commands**

```markdown
# mem-wiki

Minimal FastAPI skeleton for the middleware delegator.

## Run

```bash
uvicorn server.main:app --reload
```

Server URL: `http://127.0.0.1:8000`

## Smoke Checks

```bash
curl -s http://127.0.0.1:8000/health
curl -s "http://127.0.0.1:8000/query?q=test&limit=3"
curl -s -X POST "http://127.0.0.1:8000/ingest" \
  -H "Content-Type: application/json" \
  -d '{"question":"Q","answer":"A"}'
```
```

- [ ] **Step 2: Verify README commands end-to-end**

Run in order:

```bash
uvicorn server.main:app --reload
curl -s http://127.0.0.1:8000/health
curl -s "http://127.0.0.1:8000/query?q=test&limit=3"
curl -s -X POST "http://127.0.0.1:8000/ingest" -H "Content-Type: application/json" -d '{"question":"Q","answer":"A"}'
```

Expected results:

- `/health` returns `{"status":"ok"}`
- `/query` returns structured empty payload
- `/ingest` returns `202` JSON with `status`, `ingest_id`, `queued_at`

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add minimal run and smoke-check instructions"
```

---

### Task 3: Final Milestone Verification

**Files:**
- Modify: none (verification only)

- [ ] **Step 1: Run final contract verification commands**

```bash
curl -i http://127.0.0.1:8000/health
curl -i "http://127.0.0.1:8000/query?q=contract"
curl -i -X POST "http://127.0.0.1:8000/ingest" -H "Content-Type: application/json" -d '{"x":1}'
```

Expected key checks:

- `/health` => `200`
- `/query?q=...` => `200` with `query/results/total/summarized_answer`
- `/ingest` => `202` with `status/ingest_id/queued_at`

- [ ] **Step 2: Confirm out-of-scope boundaries were preserved**

Manual checklist:

- No SQLite setup files added
- No queue worker added
- No Ollama integration code added
- No `.env` settings model added
- No test suite introduced

- [ ] **Step 3: Commit verification checkpoint**

```bash
git status
```

Expected output:

```text
nothing to commit, working tree clean
```

---

## Self-Review

- **Spec coverage:** Plan includes all approved deliverables:
  - `server/main.py` with 3 endpoints
  - minimal `README.md` run instructions
  - contract-shaped responses and `202` behavior for `/ingest`
  - manual smoke verification path
- **Placeholder scan:** No TODO/TBD placeholders.
- **Type consistency:** Response keys and route names are consistent across tasks and checks.
