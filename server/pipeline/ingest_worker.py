"""Async ingest pipeline: Ollama → raw JSON → markdown wiki → SQLite FTS."""

from asyncio import Queue
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import aiosqlite

from server.config import Settings
from server.ollama.client import ollama_generate_json, ollama_generate_text
from server.pipeline import wiki_files
from server.pipeline.prompts import SUMMARIZE_PROMPT, WIKI_PAGE_PROMPT
from server.pipeline.textutil import one_line, slugify

logger = logging.getLogger(__name__)


@dataclass
class IngestJob:
    """Queued unit of work after HTTP 202."""

    ingest_id: str
    question: str
    answer: str
    source: str
    session_id: str | None
    tags: list[str]
    received_at: datetime


def _strip_frontmatter(md: str) -> str:
    if not md.startswith("---"):
        return md
    end = md.find("\n---\n", 3)
    if end == -1:
        return md
    return md[end + 5 :].lstrip()


async def run_ingest_pipeline(job: IngestJob, settings: Settings) -> None:
    """Run full s2 ingest: summarize, wiki markdown, raw JSON, DB + FTS, index/log."""
    settings.wiki_dir.mkdir(parents=True, exist_ok=True)
    (settings.wiki_dir / "concepts").mkdir(parents=True, exist_ok=True)

    received_iso = job.received_at.astimezone(timezone.utc).isoformat()
    now_iso = datetime.now(timezone.utc).isoformat()

    try:
        summary = await ollama_generate_json(
            settings.ollama_host,
            settings.ollama_model,
            SUMMARIZE_PROMPT.format(question=job.question, answer=job.answer),
            timeout=settings.ollama_timeout,
        )
    except Exception:
        logger.exception("summarize failed for %s; using fallback atom", job.ingest_id)
        summary = {
            "atom": one_line(job.answer, 400),
            "key_claims": [],
            "detected_topics": [],
            "detected_entities": [],
        }

    atom = str(summary.get("atom") or "").strip() or one_line(job.answer, 400)
    key_claims = summary.get("key_claims") or []
    if not isinstance(key_claims, list):
        key_claims = []
    key_claims = [str(c) for c in key_claims if c]
    topics = summary.get("detected_topics") or []
    if not isinstance(topics, list):
        topics = []
    topics = [str(t) for t in topics if t]
    entities = summary.get("detected_entities") or []
    if not isinstance(entities, list):
        entities = []
    entities = [str(e) for e in entities if e]

    user_tags = [str(t) for t in job.tags]
    merged_tags = list(dict.fromkeys([*user_tags, *topics]))[:25]

    primary = topics[0] if topics else one_line(job.question, 80)
    page_id = slugify(str(primary))
    rel_path = f"wiki/concepts/{page_id}.md"
    page_path = settings.wiki_dir / "concepts" / f"{page_id}.md"
    title = (
        str(primary).replace("-", " ").strip().title()
        if topics
        else one_line(job.question, 80)
    )

    existing = ""
    if page_path.exists():
        existing = _strip_frontmatter(page_path.read_text(encoding="utf-8"))
    existing_display = existing if existing.strip() else "EMPTY"
    claims_text = "\n".join(f"- {c}" for c in key_claims) or "- (none)"

    try:
        wiki_body = await ollama_generate_text(
            settings.ollama_host,
            settings.ollama_model,
            WIKI_PAGE_PROMPT.format(
                existing=existing_display,
                atom=atom,
                claims=claims_text,
            ),
            timeout=settings.ollama_timeout,
        )
    except Exception:
        logger.exception("wiki writer failed for %s; using atom fallback", job.ingest_id)
        wiki_body = f"## Summary\n\n{atom}\n\n## Key claims\n\n{claims_text}\n"

    tags_json = json.dumps(merged_tags)
    sources_yaml = json.dumps([job.ingest_id])
    title_esc = title.replace('"', "'")
    frontmatter = (
        "---\n"
        f"id: {page_id}\n"
        f'title: "{title_esc}"\n'
        "type: concept\n"
        f"tags: {tags_json}\n"
        "confidence: medium\n"
        f"created: {received_iso[:10]}\n"
        f"updated: {now_iso[:10]}\n"
        f"sources: {sources_yaml}\n"
        "---\n\n"
    )
    full_md = frontmatter + wiki_body.strip() + "\n"
    page_path.write_text(full_md, encoding="utf-8")

    day_dir = settings.raw_dir / job.received_at.astimezone(timezone.utc).strftime("%Y-%m-%d")
    day_dir.mkdir(parents=True, exist_ok=True)
    raw_doc: dict[str, Any] = {
        "ingest_id": job.ingest_id,
        "received_at": received_iso,
        "source": job.source,
        "session_id": job.session_id,
        "original": {"question": job.question, "answer": job.answer},
        "summary": {
            "atom": atom,
            "key_claims": key_claims,
            "detected_topics": topics,
            "detected_entities": entities,
        },
        "wiki_page": rel_path,
        "model": settings.ollama_model,
        "tags": merged_tags,
    }
    (day_dir / f"{job.ingest_id}.json").write_text(
        json.dumps(raw_doc, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    async with aiosqlite.connect(settings.db_path) as db:
        cur = await db.execute(
            "SELECT created_at, inbound_links FROM pages WHERE id = ?",
            (page_id,),
        )
        row = await cur.fetchone()
        if row:
            created_at, inbound = str(row[0]), int(row[1] or 0)
        else:
            created_at, inbound = now_iso, 0

        await db.execute(
            """
            INSERT INTO pages (id, title, type, path, tags, confidence, created_at, updated_at, inbound_links, content)
            VALUES (?, ?, 'concept', ?, ?, 'medium', ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              title = excluded.title,
              path = excluded.path,
              tags = excluded.tags,
              updated_at = excluded.updated_at,
              content = excluded.content
            """,
            (page_id, title, rel_path, tags_json, created_at, now_iso, inbound, full_md),
        )

        await db.execute("DELETE FROM pages_fts WHERE page_id = ?", (page_id,))
        await db.execute(
            "INSERT INTO pages_fts(page_id, title, content, tags) VALUES (?, ?, ?, ?)",
            (page_id, title, full_md, tags_json),
        )

        await db.execute(
            """
            INSERT INTO qa_pairs (id, page_id, question, answer, atom, tags, source, session_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job.ingest_id,
                page_id,
                job.question,
                job.answer,
                atom,
                tags_json,
                job.source,
                job.session_id,
                now_iso,
            ),
        )
        await db.execute("DELETE FROM qa_fts WHERE qa_id = ?", (job.ingest_id,))
        await db.execute(
            "INSERT INTO qa_fts(qa_id, question, answer, atom, tags) VALUES (?, ?, ?, ?, ?)",
            (job.ingest_id, job.question, job.answer, atom, tags_json),
        )
        await db.commit()

    wiki_files.append_ingest_log(
        settings.wiki_dir,
        one_line(job.question, 72),
        f"Ingest `{job.ingest_id}` → `{rel_path}`",
    )
    wiki_files.append_index_entry(settings.wiki_dir, page_id, atom)


async def ingest_worker_loop(queue: Queue[IngestJob], settings: Settings) -> None:
    """Drain ingest queue until cancelled."""
    while True:
        job = await queue.get()
        try:
            await run_ingest_pipeline(job, settings)
        except Exception:
            logger.exception("ingest pipeline failed for %s", job.ingest_id)
        finally:
            queue.task_done()
