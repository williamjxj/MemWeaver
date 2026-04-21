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
