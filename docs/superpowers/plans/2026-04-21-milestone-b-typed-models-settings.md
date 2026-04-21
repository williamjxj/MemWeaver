# Milestone B Typed Models and Settings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Design spec:** [`2026-04-21-milestone-b-typed-models-settings-design.md`](../specs/2026-04-21-milestone-b-typed-models-settings-design.md)

**Goal:** Add typed request/response models and typed settings scaffolding while preserving Milestone A behavior and avoiding DB/queue/Ollama implementation.

**Architecture:** Introduce a small `server/models` and `server/config` layer, then wire `server/main.py` routes to use explicit models. Keep runtime logic mock/static and backward-compatible for the current contract.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, pydantic-settings

---

## File Structure

- Create: `server/models/api.py` — API request/response models for ingest/query/health.
- Create: `server/config/settings.py` — typed app settings via `BaseSettings`.
- Create: `server/config/__init__.py` — config package export.
- Modify: `server/main.py` — switch to typed models and settings usage.
- Modify: `README.md` — add minimal env/settings section for local run.
- Add: `requirements.txt` — declared runtime dependencies (see design spec).

---

### Task 1: Add Typed API Models

**Files:**
- Create: `server/models/api.py`

- [x] **Step 1: Create model file with explicit contracts**

```python
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    """Permissive ingest request payload for milestone B."""

    payload: Any = None


class IngestResponse(BaseModel):
    """Response contract for POST /ingest."""

    status: str = Field(default="accepted")
    ingest_id: str
    queued_at: datetime


class QueryResponse(BaseModel):
    """Response contract for GET /query."""

    query: str
    results: list[dict[str, Any]] = Field(default_factory=list)
    total: int = 0
    summarized_answer: str | None = None


class HealthResponse(BaseModel):
    """Response contract for GET /health."""

    status: str = "ok"
```

**Implementation note:** The repository uses `RootModel[Any]` for the permissive ingest body so clients may send a top-level JSON array or object (matching the Step 2 verification snippet and `docs/s2-claude-plan.md` evolution). The snippet above shows the `payload`-field alternative; prefer the design spec for the canonical contract.

- [x] **Step 2: Verify models import cleanly**

Run:

```bash
python3 - <<'PY'
from server.models.api import IngestRequest, IngestResponse, QueryResponse, HealthResponse
print(IngestRequest.model_validate({"k": "v"}).model_dump())
print(IngestRequest.model_validate(["array-ok"]).model_dump())
print(HealthResponse().model_dump())
PY
```

Expected output contains dictionaries and no traceback.

- [x] **Step 3: Commit**

```bash
git add server/models/api.py
git commit -m "feat: add typed API models for ingest query and health"
```

---

### Task 2: Add Typed Settings Scaffold

**Files:**
- Create: `server/config/settings.py`
- Create: `server/config/__init__.py`

- [x] **Step 1: Create settings model**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed runtime settings for the API server."""

    app_name: str = "LLM-Wiki Middleware Delegator"
    app_env: str = "development"
    host: str = "127.0.0.1"
    port: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


def get_settings() -> Settings:
    return Settings()
```

- [x] **Step 2: Create package export**

```python
from .settings import Settings, get_settings

__all__ = ["Settings", "get_settings"]
```

- [x] **Step 3: Verify settings defaults**

Run:

```bash
python3 - <<'PY'
from server.config import get_settings
s = get_settings()
print(s.app_name, s.host, s.port)
PY
```

Expected output:

```text
LLM-Wiki Middleware Delegator 127.0.0.1 8000
```

- [x] **Step 4: Commit**

```bash
git add server/config/settings.py server/config/__init__.py
git commit -m "feat: add typed settings scaffold with pydantic-settings"
```

---

### Task 3: Wire Models and Settings into FastAPI App

**Files:**
- Modify: `server/main.py`

- [x] **Step 1: Update route signatures and response models**

Replace `server/main.py` with:

```python
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import Body, FastAPI, Query
from fastapi.responses import JSONResponse

from server.config import get_settings
from server.models.api import HealthResponse, IngestResponse, QueryResponse

settings = get_settings()
app = FastAPI(title=settings.app_name)


@app.post("/ingest", response_model=IngestResponse)
async def ingest(payload: Any = Body(default=None)) -> JSONResponse:
    _ = payload
    return JSONResponse(
        status_code=202,
        content={
            "status": "accepted",
            "ingest_id": f"ing_{uuid4().hex[:12]}",
            "queued_at": datetime.now(timezone.utc).isoformat(),
        },
    )


@app.get("/query", response_model=QueryResponse)
async def query(
    q: str = Query(..., description="Search query"),
    limit: int = Query(5, ge=1),
) -> QueryResponse:
    _ = limit
    return QueryResponse(query=q)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse()
```

- [x] **Step 2: Run behavior verification**

Run:

```bash
python3 - <<'PY'
from fastapi.testclient import TestClient
from server.main import app

c = TestClient(app)
print("health", c.get("/health").status_code, c.get("/health").json())
print("query", c.get("/query", params={"q":"typed"}).status_code, c.get("/query", params={"q":"typed"}).json())
resp = c.post("/ingest", json=["array-ok"])
print("ingest", resp.status_code, resp.json()["status"], resp.json()["ingest_id"].startswith("ing_"))
print("query-missing-q", c.get("/query").status_code)
PY
```

Expected checks:

- `health` status `200` + `{"status":"ok"}`
- `query` status `200` + expected structured keys
- `ingest` status `202` + status `accepted` + `ing_` prefix
- missing `q` returns `422`

- [x] **Step 3: Commit**

```bash
git add server/main.py
git commit -m "refactor: wire typed models and settings into FastAPI routes"
```

---

### Task 4: Update README for Settings-Aware Run

**Files:**
- Modify: `README.md`

- [x] **Step 1: Add minimal settings section**

Append/update README with:

```markdown
## Settings

Runtime settings are loaded from environment variables (and optional `.env`):

- `APP_NAME` (default: `LLM-Wiki Middleware Delegator`)
- `APP_ENV` (default: `development`)
- `HOST` (default: `127.0.0.1`)
- `PORT` (default: `8000`)

Example:

```bash
APP_ENV=development uvicorn server.main:app --reload
```
```

- [x] **Step 2: Verify README command still works**

Run:

```bash
uvicorn server.main:app --reload
```

Expected:

```text
Uvicorn running on http://127.0.0.1:8000
```

- [x] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: document typed settings defaults and run usage"
```

---

### Task 5: Milestone B Final Verification

**Files:**
- Modify: none

- [x] **Step 1: Verify scope boundaries**

Run:

```bash
git diff --name-only main...HEAD
```

Expected files only in scope:

- `server/models/api.py`
- `server/config/settings.py`
- `server/config/__init__.py`
- `server/main.py`
- `README.md`
- `requirements.txt`

- [x] **Step 2: Verify no forbidden additions**

Manual checklist:

- No DB schema/migration files
- No queue worker code
- No Ollama client code
- No persistence/file-writer logic

- [x] **Step 3: Final status check**

Run:

```bash
git status
```

Expected:

```text
nothing to commit, working tree clean
```

---

## Self-Review

- **Spec coverage:** Plan addresses Milestone B goals: typed API models + typed settings + route wiring + minimal docs update. Formal acceptance criteria live in `docs/superpowers/specs/2026-04-21-milestone-b-typed-models-settings-design.md`.
- **Placeholder scan:** No TODO/TBD placeholders.
- **Type consistency:** Route signatures and response models align across tasks.
