"""Initialize SQLite schema for wiki + Q/A indexing."""

from pathlib import Path

import aiosqlite

from server.config import Settings


def _migration_sql() -> str:
    path = Path(__file__).resolve().parent / "migrations" / "001_init.sql"
    return path.read_text(encoding="utf-8")


async def init_db(settings: Settings) -> None:
    """Create database file and apply initial migration if `pages` is missing."""
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(settings.db_path) as db:
        cur = await db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='pages' LIMIT 1"
        )
        row = await cur.fetchone()
        if row is None:
            await db.executescript(_migration_sql())
            await db.commit()


def fts_match_terms(query: str) -> str:
    """Build an FTS5 MATCH string (OR of quoted tokens)."""
    parts = [p for p in query.strip().split() if p]
    if not parts:
        return '""'
    escaped = []
    for p in parts:
        safe = p.replace('"', '""')
        escaped.append(f'"{safe}"')
    return " OR ".join(escaped)
