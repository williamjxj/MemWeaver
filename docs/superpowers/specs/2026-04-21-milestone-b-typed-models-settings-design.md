# Milestone B — Typed API Models and Settings

## Goal

Layer explicit **Pydantic v2** request and response models plus **`pydantic-settings`** configuration on top of the Milestone A FastAPI skeleton, without changing observable HTTP contracts or adding persistence, queues, or Ollama.

This milestone bridges `docs/superpowers/specs/2026-04-21-fastapi-skeleton-design.md` and the longer-term architecture in `docs/s2-claude-plan.md` by making route contracts and app metadata **typed and documented in code**, while keeping handlers mock-only.

## Relationship to Other Docs

| Document | Role |
|----------|------|
| `docs/superpowers/specs/2026-04-21-fastapi-skeleton-design.md` | Milestone A: single-file app, no settings module |
| **This spec** | Milestone B: `server/models`, `server/config`, typed routes |
| `docs/superpowers/plans/2026-04-21-milestone-b-typed-models-settings.md` | Executable checklist for implementing this spec |
| `docs/s2-claude-plan.md` | Target product: SQLite, FTS5, Ollama, markdown wiki (later milestones) |

## Scope

### In scope

- `server/models/api.py` — response models for `/ingest`, `/query`, `/health`; permissive ingest body typing that accepts **any JSON value** (object, array, scalar, or null) for early client integration.
- `server/config/settings.py` — `Settings` via `BaseSettings` and `get_settings()` factory.
- `server/config/__init__.py` — export `Settings`, `get_settings`.
- `server/main.py` — `FastAPI(title=settings.app_name)`; routes declare `response_model` and return typed models (or equivalent serialized output); `/ingest` remains **202 Accepted** with the same JSON keys as Milestone A.
- `README.md` — document env-driven settings (`APP_NAME`, `APP_ENV`, `HOST`, `PORT`) and local run.
- Root **`requirements.txt`** — pin minimum versions for `fastapi`, `uvicorn`, `pydantic`, `pydantic-settings`, and **`httpx`** (required by Starlette’s `TestClient` when running the plan’s ad hoc verification snippets).

### Out of scope (unchanged from Milestone A intent)

- SQLite schema, migrations, FTS5
- Background ingest workers and async pipeline
- Ollama or other LLM clients
- Wiki/raw file writers
- Committed automated test suite (manual or ad hoc `TestClient` snippets in the plan remain sufficient for B)

## Architecture

- **Models** live in `server/models/api.py`. Handlers stay thin; validation is schema-level only.
- **Settings** live in `server/config/settings.py`, loaded from environment variables and optional `.env` (`SettingsConfigDict(env_file=".env", extra="ignore")`).
- **No dependency-injection framework** beyond FastAPI defaults and a module-level `settings = get_settings()` for `app` title (matches the implementation plan; DI for `Settings` can come in a later milestone).

### Permissive ingest body

Milestone A accepted arbitrary JSON. Milestone B preserves that behavior, including **top-level JSON arrays** (used in the plan’s verification snippet).

Implementation note: a `BaseModel` with a single `payload` field does **not** accept a raw array as the whole body. This spec therefore allows either:

- `pydantic.RootModel[Any]` wrapping the entire decoded JSON value, or  
- `typing.Any` with `Body(default=None)` and responses still built with `IngestResponse`.

Both satisfy “permissive ingest” and the acceptance checks in the Milestone B plan.

## Endpoint Design

Behavior and status codes match `2026-04-21-fastapi-skeleton-design.md` unless noted below.

### `POST /ingest`

- **Status:** `202 Accepted`
- **Response model:** `IngestResponse` with `status` (default semantic `"accepted"`), `ingest_id` (`ing_` prefix + random suffix), `queued_at` as **UTC datetime** (serialized ISO-8601 in JSON).
- **Request:** any JSON; handler does not persist or enqueue real work.

### `GET /query`

- **Query params:** `q` (required), `limit` (optional, default `5`, minimum `1`).
- **Response model:** `QueryResponse` — `query`, `results` (empty list), `total` (`0`), `summarized_answer` (`null`).
- Missing `q` → **422** via FastAPI validation.

### `GET /health`

- **Status:** `200`
- **Response model:** `HealthResponse` with `status: "ok"`.

## Settings and Environment Variables

| Field | Env var (typical) | Default |
|-------|-------------------|---------|
| `app_name` | `APP_NAME` | `LLM-Wiki Middleware Delegator` |
| `app_env` | `APP_ENV` | `development` |
| `host` | `HOST` | `127.0.0.1` |
| `port` | `PORT` | `8000` |

`PORT` and `HOST` inform documented run examples; binding is still usually chosen by the `uvicorn` CLI unless wired later.

## Alignment with `docs/s2-claude-plan.md`

- Response keys for `/query` and fields for `/ingest` acceptance remain compatible with the planned client and with the richer ingest schema (`question`, `answer`, …) to be introduced in a **later** milestone; this milestone does **not** implement that schema yet.
- Settings names should remain stable so deployment (Docker, systemd, etc.) can set `APP_NAME` / `APP_ENV` without churn.

## Testing Approach

- Manual smoke: `curl` examples in `README.md` (same three routes as Milestone A).
- Optional one-off script in the implementation plan using `TestClient` to assert status codes and shapes (`/ingest` with a JSON array body, `/query` without `q` → 422).

## Deliverables

- `server/models/api.py`
- `server/config/settings.py`, `server/config/__init__.py`
- `server/main.py` (typed routes and settings-backed app title)
- `README.md` (settings + install referencing `requirements.txt`)
- `requirements.txt`
- This specification file

## Acceptance Criteria

- Application starts with `uvicorn server.main:app --reload` after `pip install -r requirements.txt`.
- `/health` returns `200` and `{"status":"ok"}`.
- `/query?q=…` returns `200` and a payload matching `QueryResponse` (including `summarized_answer: null` when absent).
- `/ingest` with arbitrary JSON (including a top-level array) returns `202` and payload matching `IngestResponse`.
- Settings defaults match the table above; overrides via env vars work.
- No database, queue worker, Ollama client, or file-writer code added under `server/` for this milestone.

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Typed ingest prematurely breaks permissive clients | Use `RootModel[Any]` or `Body` + `Any`; document in this spec |
| `response_model` changes serialization (e.g. datetime) | Accept ISO strings in JSON; clients already expect structured JSON |
| Drift from s2 plan field names | Keep `QueryResponse` / `IngestResponse` keys aligned with s2 until a dedicated “ingest schema v2” milestone |

## Next Milestone Preview

- Persist Q/A and wiki artifacts (SQLite + markdown paths per `docs/s2-claude-plan.md`).
- Background tasks for ingest pipeline after returning `202`.
- Ollama client and summarization prompts.
- Optional: pytest suite and CI (deferred from Milestones A and B by scope).
