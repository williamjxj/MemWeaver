"""HTTP API Pydantic models (s2-aligned)."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class QueryMode(str, Enum):
    """Search mode for ``GET /query``."""

    KEYWORD = "keyword"  # FTS5 BM25 only
    SEMANTIC = "semantic"  # Vector cosine similarity only
    HYBRID = "hybrid"  # FTS5 + vector merged via Reciprocal Rank Fusion


class IngestPayload(BaseModel):
    """Structured ingest body per docs/v2/s2-claude-plan.md §3.1."""

    question: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=1)
    source: str = "unknown"
    session_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    timestamp: datetime | None = None


class IngestResponse(BaseModel):
    """Response contract for POST /ingest."""

    status: str = Field(default="accepted")
    ingest_id: str
    queued_at: datetime


class QueryResponse(BaseModel):
    """Response contract for GET /query."""

    query: str
    mode: QueryMode = QueryMode.HYBRID
    results: list[dict[str, Any]] = Field(default_factory=list)
    total: int = 0
    summarized_answer: str | None = None


class HealthResponse(BaseModel):
    """Response contract for GET /health (s2 §3.3 + localhost defaults)."""

    status: str = "ok"
    ollama: str | None = None
    db: str | None = None
    queue_depth: int | None = None
    wiki_pages: int | None = None
    qa_pairs: int | None = None


class ChatRequest(BaseModel):
    """Request body for POST /chat (streaming)."""

    question: str = Field(..., min_length=1)


class WikiResponse(BaseModel):
    """Response body for GET /wiki/{slug}."""

    slug: str
    content: str


class StatsResponse(BaseModel):
    """Aggregate counters (s2 §3.4)."""

    total_ingests: int = 0
    total_wiki_pages: int = 0
    top_tags: list[list[str | int]] = Field(default_factory=list)
    last_ingest: str | None = None
    orphan_pages: int = 0
