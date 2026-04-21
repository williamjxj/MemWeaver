"""Append-only updates to `wiki/index.md` and `wiki/log.md`."""

from datetime import datetime, timezone
from pathlib import Path

from server.pipeline.textutil import one_line


def append_ingest_log(wiki_dir: Path, title: str, detail: str) -> None:
    """Append a grep-friendly ingest entry to `wiki/log.md`."""
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_path = wiki_dir / "log.md"
    block = f"\n## [{day}] ingest | {title}\n\n{detail}\n"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if log_path.exists():
        log_path.write_text(log_path.read_text(encoding="utf-8") + block, encoding="utf-8")
    else:
        log_path.write_text("# Wiki log\n" + block, encoding="utf-8")


def append_index_entry(wiki_dir: Path, slug: str, summary_line: str) -> None:
    """Append a catalog line under `## Auto-index (pipeline)` when missing."""
    idx = wiki_dir / "index.md"
    marker = "## Auto-index (pipeline)"
    link = f"[[{slug}]]"
    if idx.exists():
        text = idx.read_text(encoding="utf-8")
    else:
        text = "# Wiki index\n"
    if link in text:
        return
    if marker not in text:
        text = text.rstrip() + f"\n\n{marker}\n\n"
    text += f"- {link} — {one_line(summary_line, 160)}\n"
    idx.parent.mkdir(parents=True, exist_ok=True)
    idx.write_text(text, encoding="utf-8")
