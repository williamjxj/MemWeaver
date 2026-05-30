"""FastAPI delegator: ingest (async pipeline), FTS query, chat (SSE), health, stats."""

import asyncio
import json
import logging
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timezone

import aiosqlite
import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from server.config import get_settings
from server.db.database import init_db
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
from server.services.public_llm import stream_ollama_chat
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


@app.post("/chat")
async def chat(req: ChatRequest):
    """Streaming chat endpoint. Classifies topic, retrieves wiki context,
    streams Ollama response via SSE, then enqueues background wiki compilation."""
    cfg = app.state.settings

    topic, slugs = classify_topic(req.question)
    if not any(slugs):
        topic = await classify_with_ollama(req.question, cfg)
        slugs = SKILL_TAXONOMY[topic]["wiki_paths"]  # type: ignore[union-attr]

    slug, summary = await retrieve_summary(req.question, slugs, cfg)

    async def event_stream():
        full_answer = ""
        try:
            async for token in stream_ollama_chat(req.question, summary, cfg):
                full_answer += token
                yield f"event: token\ndata: {json.dumps({'text': token})}\n\n"
        except Exception:
            logger.exception("chat streaming failed")
            yield f"event: error\ndata: {json.dumps({'message': 'Ollama stream failed'})}\n\n"
            return

        yield (
            f"event: done\n"
            f"data: {json.dumps({'wiki_slug': slug, 'topic': topic, 'context_chars': len(summary)})}\n\n"
        )

        # Phase B: enqueue wiki compilation in the background
        if full_answer.strip():
            try:
                await memory_api.enqueue_ingest(
                    cfg,
                    app.state.ingest_queue,
                    question=req.question.strip(),
                    answer=full_answer.strip(),
                    source="chat",
                    tags=[topic],
                )
            except Exception:
                logger.exception("failed to enqueue background compilation for chat")

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
