# MemWeaver — Copilot Instructions

- Overview: FastAPI backend (`server/`) and Next.js frontend (`chat-app/`).
- Languages & tooling: Python 3.12, Node 20, pnpm, Next.js 16, Tailwind CSS / shadcn/ui.
- Local LLM: Ollama is required for local LLM calls. Default host: `http://127.0.0.1:11434`. Set `OLLAMA_HOST` / `OLLAMA_MODEL` via `.env`. Pipeline code must NOT call external LLM APIs.
- Data stores: SQLite + FTS5 + sqlite-vec for semantic search; wiki content lives in `wiki/` and raw ingests in `raw/`.

- Quick setup
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

- Run backend (development)
```bash
uvicorn server.main:app --reload
```

- Run frontend (development)
```bash
cd chat-app
pnpm install
pnpm dev
```

- Tests & smoke checks
```bash
./venv/bin/pytest tests/ -v
./scripts/smoke-check.sh
```

- Important routes & paths: `server/`, `chat-app/`, `wiki/`, `raw/`; API endpoints include `/ingest`, `/query`, `/chat` (SSE), `/wiki/{slug}`.
- Conventions: Conventional Commits; Python style (snake_case, 4-space indent); async I/O; Pydantic v2 for models. See `AGENTS.md` and `CLAUDE.md` for full operational details.

- If in doubt, follow the repo docs: `AGENTS.md` and `CLAUDE.md`.