"""Initialize SQLite schema for wiki + Q/A indexing + semantic search."""

from pathlib import Path

import aiosqlite

from server.config import Settings
from server.db.vec import load_vec


def _migration_sql(name: str) -> str:
    path = Path(__file__).resolve().parent / "migrations" / name
    return path.read_text(encoding="utf-8")


async def init_db(settings: Settings) -> None:
    """Create database file and apply migrations (schema + vec0)."""
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(settings.db_path, check_same_thread=False) as db:
        # Migration 001: core tables + FTS5
        cur = await db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='pages' LIMIT 1"
        )
        row = await cur.fetchone()
        if row is None:
            await db.executescript(_migration_sql("001_init.sql"))
            await db.commit()

        # Migration 002: page_embeddings vec0 table
        await load_vec(db)
        cur = await db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='page_embeddings' LIMIT 1"
        )
        row = await cur.fetchone()
        if row is None:
            await db.executescript(_migration_sql("002_semantic_search.sql"))
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
