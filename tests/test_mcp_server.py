"""In-process FastMCP smoke tests (no subprocess)."""

import json
from pathlib import Path
from typing import Any

import pytest
from fastmcp import Client

from server.mcp_server import mcp


def _tool_payload(result: Any) -> dict[str, Any]:
    """Parse FastMCP 3.x tool result (content text or .data)."""
    data = getattr(result, "data", None)
    if data is not None:
        if isinstance(data, str):
            return json.loads(data)
        if isinstance(data, dict):
            return data
    text = result.content[0].text
    return json.loads(text)


@pytest.fixture
def mcp_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    base = tmp_path / "mw"
    base.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("DB_PATH", str(base / "wiki.db"))
    monkeypatch.setenv("WIKI_DIR", str(base / "wiki"))
    monkeypatch.setenv("RAW_DIR", str(base / "raw"))
    monkeypatch.setenv("DLQ_DIR", str(base / "failed"))
    monkeypatch.setenv("OLLAMA_HOST", "http://127.0.0.1:9")
    return base


@pytest.mark.asyncio
async def test_mcp_lists_four_tools(mcp_env: Path) -> None:
    async with Client(mcp) as client:
        tools = await client.list_tools()
    names = {t.name for t in tools}
    assert names == {"wiki_search", "wiki_ingest", "wiki_get_page", "wiki_stats"}


@pytest.mark.asyncio
async def test_mcp_wiki_stats_call(mcp_env: Path) -> None:
    async with Client(mcp) as client:
        result = await client.call_tool("wiki_stats", {})
    payload = _tool_payload(result)
    assert "wiki_pages" in payload
    assert payload["ollama"] in {"reachable", "unreachable"}
