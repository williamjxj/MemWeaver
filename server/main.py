"""FastAPI skeleton routes for ingest, query, and health."""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, Query

app = FastAPI()


@app.post("/ingest", status_code=202)
async def ingest(payload: dict) -> dict:
    """Queue an ingest request with a permissive payload."""
    _ = payload
    return {
        "status": "accepted",
        "ingest_id": str(uuid4()),
        "queued_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/query")
async def query(
    q: str = Query(..., description="Search query"),
    limit: int = Query(5, ge=1, description="Maximum number of results"),
) -> dict:
    """Return a placeholder query response."""
    _ = limit
    return {
        "query": q,
        "results": [],
        "total": 0,
        "summarized_answer": None,
    }


@app.get("/health")
async def health() -> dict:
    """Return service health status."""
    return {"status": "ok"}
