"""FastAPI delegator: ingest (async pipeline), FTS query, chat (SSE), health, stats."""

import asyncio
import json
import logging
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite
import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from server.config import get_settings
from server.db.database import init_db
from server.db.vec import load_vec
from server.models.api import (
    ChatRequest,
    GraphResponse,
    HealthResponse,
    IngestPayload,
    IngestResponse,
    QueryMode,
    QueryResponse,
    StatsResponse,
    WikiResponse,
)
from server.pipeline.ingest_worker import ingest_worker_loop
from server.pipeline.query_search import synthesize_answer
from server.services import memory_api, wiki_graph_api, wiki_tree_api
from server.services.classifier import SKILL_TAXONOMY, classify_topic, classify_with_ollama
from server.services.memory_api import IngestQueueFullError
from server.services.public_llm import build_messages, stream_chat
from server.services.wiki_retriever import retrieve_summary

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    await init_db(settings)
    app.state.settings = settings
    app.state.ingest_queue = asyncio.Queue(maxsize=settings.max_queue_size)
    app.state.worker_task = asyncio.create_task(
        ingest_worker_loop(app.state.ingest_queue, settings)
    )
    yield
    app.state.worker_task.cancel()
    with suppress(asyncio.CancelledError):
        await app.state.worker_task


settings = get_settings()
app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/ingest", response_model=IngestResponse, status_code=202)
async def ingest(payload: IngestPayload) -> IngestResponse:
    """Accept Q/A, return 202; Ollama + wiki + DB run on a background worker."""
    cfg = app.state.settings
    received = payload.timestamp or datetime.now(timezone.utc)
    if received.tzinfo is None:
        received = received.replace(tzinfo=timezone.utc)
    try:
        result = await memory_api.enqueue_ingest(
            cfg,
            app.state.ingest_queue,
            question=payload.question,
            answer=payload.answer,
            source=payload.source or "unknown",
            tags=payload.tags,
            session_id=payload.session_id,
            received_at=received,
            note=payload.note,
        )
    except IngestQueueFullError as err:
        raise HTTPException(status_code=503, detail="ingest queue is full") from err
    return IngestResponse(
        status="accepted",
        ingest_id=result["ingest_id"],
        queued_at=datetime.now(timezone.utc),
    )


@app.get("/query", response_model=QueryResponse)
async def query(
    q: str = Query(..., description="Search query"),
    limit: int = Query(5, ge=1, le=50),
    mode: QueryMode = Query(
        QueryMode.HYBRID,
        description="Search mode: keyword (FTS5), semantic (vector), hybrid (RRF merge).",
    ),
    summarize: bool = Query(
        False,
        description="If true, run Ollama over top wiki snippets (uses extra tokens).",
    ),
) -> QueryResponse:
    cfg = app.state.settings

    payload = await memory_api.search_wiki(cfg, q, limit=limit, mode=mode)
    if payload.get("error"):
        raise HTTPException(status_code=400, detail=payload["error"])
    rows = payload["results"]

    summarized: str | None = None
    if summarize and rows:
        snippets = [str(r.get("snippet") or "") for r in rows]
        try:
            summarized = await synthesize_answer(cfg, q, snippets)
        except Exception:
            logger.exception("query summarization failed")
            summarized = None
    return QueryResponse(
        query=payload["query"],
        mode=mode,
        results=rows,
        total=payload["total"],
        summarized_answer=summarized,
    )


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    cfg = app.state.settings
    ollama_status = "reachable"
    try:
        headers = {}
        if cfg.ollama_api_key:
            headers["Authorization"] = f"Bearer {cfg.ollama_api_key}"
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{cfg.ollama_host.rstrip('/')}/api/tags", headers=headers)
            r.raise_for_status()
    except Exception:
        ollama_status = "unreachable"

    db_status = "ok"
    n_pages = 0
    n_qa = 0
    try:
        async with aiosqlite.connect(cfg.db_path) as db:
            cur = await db.execute("SELECT COUNT(*) FROM pages")
            row = await cur.fetchone()
            n_pages = int(row[0]) if row else 0
            cur = await db.execute("SELECT COUNT(*) FROM qa_pairs")
            row = await cur.fetchone()
            n_qa = int(row[0]) if row else 0
    except Exception:
        db_status = "error"

    depth = app.state.ingest_queue.qsize()
    return HealthResponse(
        status="ok",
        ollama=ollama_status,
        db=db_status,
        queue_depth=depth,
        wiki_pages=n_pages,
        qa_pairs=n_qa,
    )


@app.get("/stats", response_model=StatsResponse)
async def stats() -> StatsResponse:
    cfg = app.state.settings
    data = await memory_api.get_wiki_stats(cfg, app.state.ingest_queue)
    return StatsResponse(
        total_ingests=data["qa_pairs"],
        total_wiki_pages=data["wiki_pages"],
        top_tags=data["top_tags"],
        last_ingest=data["last_ingest"],
        orphan_pages=data["orphan_pages"],
    )


@app.get("/inventory")
async def inventory():
    """Record counts across all data stores: raw QA, wiki concepts, DB tables, index, log."""
    cfg = app.state.settings

    raw_qa: dict = {"total": 0, "by_date": {}}
    raw_base = Path(cfg.raw_dir)
    if raw_base.is_dir():
        for d in sorted(raw_base.iterdir()):
            if not d.is_dir():
                continue
            count = len(list(d.glob("*.json")))
            if count:
                raw_qa["by_date"][d.name] = count
                raw_qa["total"] += count

    concepts_dir = Path(cfg.wiki_dir) / "concepts"
    concepts = 0
    concept_files: list[dict] = []
    if concepts_dir.is_dir():
        for f in sorted(concepts_dir.glob("*.md")):
            concepts += 1
            concept_files.append({"name": f.name, "size": fmt_size(f)})

    db_info: dict = {}
    db_path = Path(cfg.db_path)
    if db_path.is_file():
        try:
            async with aiosqlite.connect(str(db_path)) as db:
                await load_vec(db)
                rows = await db.execute_fetchall(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "ORDER BY name"
                )
                all_counts: dict = {}
                for (name,) in rows:
                    try:
                        row = await db.execute_fetchall(
                            f'SELECT COUNT(*) FROM "{name}"'
                        )
                        all_counts[name] = row[0][0] if row else 0
                    except Exception:
                        all_counts[name] = "N/A"
                db_info = {
                    "pages": all_counts.get("pages", 0),
                    "qa_pairs": all_counts.get("qa_pairs", 0),
                    "wiki_links": all_counts.get("wiki_links", 0),
                    "all_tables": all_counts,
                }
        except Exception:
            db_info = {"error": "unreadable"}
        db_info["db_size"] = fmt_size(db_path)

    index_info: dict = {"total": 0, "file_lines": 0}
    index_path = Path(cfg.wiki_dir) / "index.md"
    if index_path.is_file():
        lines = index_path.read_text(encoding="utf-8").splitlines()
        in_concepts = False
        entries = 0
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("## Concepts"):
                in_concepts = True
                continue
            if in_concepts and stripped.startswith("## "):
                break
            if in_concepts and line.startswith("|") and "---" not in line and "Page" not in line:
                parts = [p.strip() for p in line.strip("|").split("|")]
                if len(parts) >= 2 and parts[0]:
                    entries += 1
        index_info = {"total": entries, "file_lines": len(lines)}
        index_info["size"] = fmt_size(index_path)

    log_info: dict = {"total": 0, "file_lines": 0}
    log_path = Path(cfg.wiki_dir) / "log.md"
    if log_path.is_file():
        lines = log_path.read_text(encoding="utf-8").splitlines()
        entries = [l for l in lines if l.strip().startswith("## ")]
        log_info = {"total": len(entries), "file_lines": len(lines)}
        log_info["size"] = fmt_size(log_path)

    return {
        "raw_qa": raw_qa,
        "concepts": {"total": concepts, "files": concept_files},
        "db": db_info,
        "index": index_info,
        "log": log_info,
    }


def fmt_size(path: Path) -> str:
    size = path.stat().st_size
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.0f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


@app.post("/chat")
async def chat(req: ChatRequest):
    """Streaming chat endpoint. Classifies topic, retrieves wiki context,
    and streams the public LLM (DeepSeek) response via SSE. Saving the turn
    to memory is opt-in via an explicit POST /ingest, not done here."""
    cfg = app.state.settings
    history = req.history or []

    topic, slugs = classify_topic(req.question)
    context_mode = "cold" if not history else ("warm" if len(history) <= 2 else "rich")

    summary = ""
    slug: str | None = None
    if history:
        if not any(slugs):
            topic = await classify_with_ollama(req.question, cfg)
            slugs = SKILL_TAXONOMY[topic]["wiki_paths"]  # type: ignore[union-attr]

        retrieval_query = req.question
        recent_user_turns = [
            turn.content.strip()
            for turn in history
            if turn.role == "user" and turn.content.strip()
        ]
        if recent_user_turns:
            retrieval_query = req.question + "\n\nRecent conversation:\n" + "\n".join(
                f"- {text}" for text in recent_user_turns[-3:]
            )

        slug, summary = await retrieve_summary(retrieval_query, slugs, cfg)

    if not history and not any(slugs):
        topic = await classify_with_ollama(req.question, cfg)
        slugs = SKILL_TAXONOMY[topic]["wiki_paths"]  # type: ignore[union-attr]

    messages = build_messages(
        req.question,
        wiki_summary=summary,
        recent_history=[turn.model_dump() for turn in history],
        model_label=cfg.deepseek_model,
    )

    async def event_stream():
        if not cfg.deepseek_api_key:
            yield f"event: error\ndata: {json.dumps({'message': 'DEEPSEEK_API_KEY is not configured'})}\n\n"
            return
        full_answer = ""
        try:
            async for token in stream_chat(messages, cfg):
                full_answer += token
                yield f"event: token\ndata: {json.dumps({'text': token})}\n\n"
        except Exception:
            logger.exception("chat streaming failed")
            yield f"event: error\ndata: {json.dumps({'message': 'chat stream failed'})}\n\n"
            return

        if not full_answer:
            logger.warning(
                "chat stream produced zero tokens — likely transient DeepSeek API issue. "
                "messages=%d, first_role=%s, last_role=%s",
                len(messages),
                messages[0]["role"] if messages else "none",
                messages[-1]["role"] if messages else "none",
            )
            yield (
                f"event: error\n"
                f"data: {json.dumps({'message': 'DeepSeek returned an empty response. Please try again.'})}\n\n"
            )
            return

        yield (
            f"event: done\n"
            f"data: {json.dumps({'wiki_slug': slug, 'topic': topic, 'context_chars': len(summary), 'context_mode': context_mode, 'history_turns': len(history)})}\n\n"
        )

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/wiki/graph", response_model=GraphResponse)
async def wiki_graph():
    """Return all wiki pages and their link relationships for the graph view."""
    cfg = app.state.settings
    data = await wiki_graph_api.get_wiki_graph(cfg)
    return GraphResponse(**data)


@app.get("/wiki/tree")
async def wiki_tree():
    """Return a sidebar-friendly wiki catalog built from wiki/index.md."""
    cfg = app.state.settings
    return await wiki_tree_api.get_wiki_tree(cfg)


@app.get("/wiki/{slug:path}", response_model=WikiResponse)
async def get_wiki(slug: str):
    """Fetch a wiki article by slug. Returns markdown content."""
    cfg = app.state.settings
    data = await memory_api.get_wiki_page(cfg, slug)
    return WikiResponse(**data)
