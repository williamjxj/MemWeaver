"""Shared wiki memory operations for HTTP routes and MCP tools."""

from __future__ import annotations

from pathlib import Path

from server.config import Settings


async def get_wiki_page(settings: Settings, slug: str) -> dict[str, str]:
    """Read wiki markdown by slug. Returns empty content if not found."""
    article_path = Path(settings.wiki_dir) / f"{slug}.md"
    if article_path.exists():
        content = article_path.read_text(encoding="utf-8")
    else:
        content = ""
    return {"slug": slug, "content": content}
