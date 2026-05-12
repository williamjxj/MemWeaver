"""sqlite-vec extension loader for aiosqlite connections."""

import logging

import aiosqlite
import sqlite_vec

logger = logging.getLogger(__name__)

LOADABLE_PATH = sqlite_vec.loadable_path()


async def load_vec(db: aiosqlite.Connection) -> None:
    """Enable sqlite-vec extension on an active aiosqlite connection.

    Must be called once per connection before any vec0 queries.
    Safe to call multiple times (idempotent via try/except).

    ``aiosqlite.Connection`` exposes async ``enable_load_extension()``
    and ``load_extension()`` that delegate to the worker thread, so
    we use those directly instead of accessing ``db._connection``.
    """
    try:
        await db.enable_load_extension(True)
        await db.load_extension(LOADABLE_PATH)
        await db.enable_load_extension(False)
    except Exception:
        logger.exception("failed to load sqlite-vec extension")
        raise
