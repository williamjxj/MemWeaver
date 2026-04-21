# FastAPI Skeleton Design

## Goal

Implement the first runnable server milestone from existing docs by adding a minimal FastAPI skeleton with stable endpoint contracts and lightweight run documentation.

This milestone is intentionally contract-first and non-functional for persistence/retrieval logic.

## Scope

### In Scope

- Add a minimal FastAPI app with:
  - `POST /ingest`
  - `GET /query`
  - `GET /health`
- Ensure route responses match the planned JSON shape closely enough for early integration.
- Add minimal local run instructions in `README.md`.

### Out of Scope

- SQLite schema, migrations, FTS5 integration
- Async ingest queue worker implementation
- Ollama integration and summarization pipeline
- Wiki/raw file persistence
- Structured config (`.env`, settings models) and production hardening
- Automated test suite

## Architecture

Use a thin vertical slice:

- `server/main.py` holds one FastAPI app and all three routes.
- Route internals return static or generated mock payloads only.
- No dependency injection, no background workers, no storage adapters yet.

Rationale:

- Keeps implementation very small and fast.
- Allows clients to integrate against stable route shapes.
- Minimizes premature abstractions that may change in later milestones.

## Endpoint Design

### `POST /ingest`

Purpose:

- Establish the ingestion contract and acceptance semantics.

Behavior:

- Accepts JSON body permissively in this milestone.
- Returns HTTP `202 Accepted`.

Response shape:

- `status`: `"accepted"`
- `ingest_id`: generated placeholder id (for example `ing_<timestamp_or_uuid>`)
- `queued_at`: current UTC time in ISO8601 format

### `GET /query`

Purpose:

- Establish retrieval contract for frontend/client integration.

Inputs:

- `q` required query parameter (string)
- `limit` optional query parameter (default `5`)

Behavior:

- Returns structured empty result set.

Response shape:

- `query`: echoed input query
- `results`: empty array
- `total`: `0`
- `summarized_answer`: `null`

### `GET /health`

Purpose:

- Provide liveness endpoint for local development checks.

Behavior:

- Returns HTTP `200` with minimal health payload.

Response shape:

- `status`: `"ok"`

## Error Handling

- Rely on FastAPI defaults for validation at this stage.
- `GET /query` should naturally return `422` when required `q` is missing.
- No custom exception middleware in this milestone.
- `POST /ingest` remains permissive to avoid blocking early client integration.

## Testing Approach

Manual smoke verification only:

1. Start app with local run command.
2. Call `GET /health` and verify `status: ok`.
3. Call `GET /query?q=test` and verify empty structured payload.
4. Call `POST /ingest` with any JSON body and verify `202` payload fields.

Automated tests are deferred to the next milestone.

## Deliverables

- `server/main.py` with three skeleton endpoints.
- `README.md` minimal run instructions (`uvicorn server.main:app --reload`).
- No additional scaffolding files unless needed to run the server.

## Acceptance Criteria

- App starts locally without additional infrastructure.
- All three routes are reachable and return the defined payload shapes.
- `/ingest` returns `202 Accepted`.
- `/query` requires `q` and returns structured empty output for valid input.
- README includes a concise run command section.

## Risks and Mitigations

- Risk: endpoint shapes drift from the longer-term plan.
  - Mitigation: keep response keys aligned with `docs/s2-claude-plan.md`.
- Risk: adding too much “future” scaffolding creates churn.
  - Mitigation: defer non-essential modules to later milestones.

## Next Milestone Preview

After this skeleton is complete, the next recommended milestone is **Milestone B** (typed models and settings), specified in:

- `docs/superpowers/specs/2026-04-21-milestone-b-typed-models-settings-design.md`
- `docs/superpowers/plans/2026-04-21-milestone-b-typed-models-settings.md`

Following Milestone B, introduce DB schema/migrations and ingest/query wiring incrementally per `docs/s2-claude-plan.md`.
