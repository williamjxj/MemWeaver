"""Fast keyword-based wiki article retrieval from _index.md."""

import logging
from pathlib import Path

from server.config import Settings

logger = logging.getLogger(__name__)

MAX_SUMMARY_CHARS = 1000  # injection cap for public LLM context (reduced to speed prompts)


def _load_index(wiki_dir: Path) -> list[dict]:
    """Parse _index.md into a list of {slug, topic, keywords, summary} dicts."""
    index_file = wiki_dir / "_index.md"
    if not index_file.exists():
        return []
    rows: list[dict] = []
    for line in index_file.read_text(encoding="utf-8").splitlines():
        if line.startswith("| ") and "---" not in line and "Slug" not in line:
            parts = [p.strip() for p in line.strip("|").split("|")]
            if len(parts) >= 4:
                rows.append({
                    "slug": parts[0],
                    "topic": parts[1],
                    "keywords": [k.strip().lower() for k in parts[2].split(",")],
                    "summary": parts[3],
                })
    return rows


async def retrieve_summary(
    question: str,
    candidate_slugs: list[str],
    settings: Settings,
) -> tuple[str | None, str]:
    """Return (best_slug, summary_text) for injection into the LLM prompt.

    Scores candidate wiki articles by keyword overlap with the question.
    Returns the full article content (truncated to MAX_SUMMARY_CHARS).
    """
    index = _load_index(settings.wiki_dir)
    q_lower = question.lower()

    scored: list[tuple[int, dict]] = []
    for entry in index:
        if entry["slug"] in candidate_slugs:
            score = sum(1 for kw in entry["keywords"] if kw in q_lower)
            scored.append((score, entry))

    if not scored:
        return None, ""

    best = max(scored, key=lambda x: x[0])
    sl = best[1]["slug"]

    article_path = settings.wiki_dir / f"{sl}.md"
    if not article_path.exists():
        return sl, best[1]["summary"]

    content = article_path.read_text(encoding="utf-8")
    return sl, content[:MAX_SUMMARY_CHARS]
