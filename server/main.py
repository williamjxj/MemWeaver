from datetime import datetime, timezone
from uuid import uuid4

from fastapi import Body, FastAPI, Query

from server.config import get_settings
from server.models.api import HealthResponse, IngestRequest, IngestResponse, QueryResponse

settings = get_settings()
app = FastAPI(title=settings.app_name)

@app.post("/ingest", response_model=IngestResponse, status_code=202)
async def ingest(request: IngestRequest = Body(default=IngestRequest(root=None))) -> IngestResponse:
    _ = request
    return IngestResponse(
        status="accepted",
        ingest_id=f"ing_{uuid4().hex[:12]}",
        queued_at=datetime.now(timezone.utc),
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
