# Repository Guidelines

## Project Structure & Module Organization
`server/` contains the runnable API. `server/main.py` defines the FastAPI app and routes `/ingest`, `/query`, `/health`, and `/stats`. Request/response schemas live in `server/models/api.py`. Runtime configuration is in `server/config/settings.py`. The ingest **worker** (`server/pipeline/ingest_worker.py`) calls Ollama, writes `raw/qa/…`, updates `wiki/concepts/…`, and syncs SQLite + FTS (`server/db/`).

`docs/` holds product notes, plans, and implementation specs. Treat it as design context, not executable code. Ignore generated `__pycache__/` directories and avoid committing local artifacts such as `.DS_Store`.

`wiki/` is the **LLM-wiki** markdown vault (index, log, concepts) for this service; `wiki/LLM_WIKI_SCHEMA.md` ties [Karpathy’s LLM-Wiki gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) and `docs/s2-claude-plan.md` to REST usage. `raw/` will hold immutable ingest JSON once the pipeline is implemented.

## Build, Test, and Development Commands
Install dependencies once:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Run the app locally with:

```bash
uvicorn server.main:app --reload
```

Use environment variables or a local `.env` file to override settings:

```bash
APP_ENV=development HOST=127.0.0.1 PORT=8000 uvicorn server.main:app --reload
```

Smoke-check the current API with:

```bash
curl -sS http://127.0.0.1:8000/health
curl -sS "http://127.0.0.1:8000/query?q=hello&limit=3"
curl -sS http://127.0.0.1:8000/stats
curl -sS -X POST http://127.0.0.1:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"question":"Smoke question?","answer":"Smoke answer.","source":"smoke-check"}'
```

Ollama must be running; default model is `minimax-m2.7:cloud` (override with `OLLAMA_MODEL`).

## Coding Style & Naming Conventions
Follow Python 3.12 conventions already used in the repo: 4-space indentation, `snake_case` for functions and variables, `PascalCase` for Pydantic models, and explicit type hints on public code paths. Keep route handlers thin; move schema and settings concerns into `server/models/` and `server/config/`.

Prefer small, typed modules over large mixed files. Use concise docstrings where the contract is not obvious.

## Testing Guidelines
Run automated tests from the project venv:

```bash
./venv/bin/pytest tests/ -v
```

Every change should still include manual smoke checks against the HTTP endpoints above when behavior changes. Add new tests under `tests/` and name files `test_<module>.py`.

## Commit & Pull Request Guidelines
Recent history uses Conventional Commit prefixes such as `feat:`, `refactor:`, and `docs:`. Keep commit messages imperative and scoped to one change, for example: `feat: add query response metadata`.

Pull requests should include a short description, the reason for the change, manual verification steps, and sample request/response output when API behavior changes.
