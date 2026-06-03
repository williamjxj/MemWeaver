#!/usr/bin/env python3
"""Inventory checker: list record counts across all mem-weaver data stores."""

import json
import sqlite3
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def count_raw_qa() -> dict:
    """Count raw QA JSON files grouped by date directory."""
    base = REPO / "raw" / "qa"
    if not base.is_dir():
        return {"total": 0, "by_date": {}}

    by_date: dict[str, int] = {}
    total = 0
    for d in sorted(base.iterdir()):
        if not d.is_dir():
            continue
        count = len(list(d.glob("*.json")))
        if count:
            by_date[d.name] = count
            total += count
    return {"total": total, "by_date": by_date}


def count_wiki_concepts() -> int:
    """Count .md files in wiki/concepts."""
    concepts = REPO / "wiki" / "concepts"
    if not concepts.is_dir():
        return 0
    return len(list(concepts.glob("*.md")))


def count_db() -> dict:
    """Count rows in key DB tables (skip vec0 virtual tables)."""
    db_path = REPO / "db" / "wiki.db"
    if not db_path.is_file():
        return {}

    conn = sqlite3.connect(str(db_path))
    try:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE '%vec%' ORDER BY name"
        ).fetchall()

        counts = {}
        for (name,) in tables:
            try:
                (count,) = conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()
                counts[name] = count
            except sqlite3.OperationalError:
                counts[name] = "N/A"

        # Separate the main content tables
        return {
            "pages": counts.get("pages", 0),
            "qa_pairs": counts.get("qa_pairs", 0),
            "wiki_links": counts.get("wiki_links", 0),
            "all_tables": counts,
        }
    finally:
        conn.close()


def count_index() -> dict:
    """Parse wiki/index.md for page entries under ## Concepts."""
    idx = REPO / "wiki" / "index.md"
    if not idx.is_file():
        return {"total": 0}

    lines = idx.read_text(encoding="utf-8").splitlines()
    in_concepts = False
    entries = 0
    for line in lines:
        if line.strip().startswith("## Concepts"):
            in_concepts = True
            continue
        if in_concepts and line.strip().startswith("## "):
            break
        # Count markdown table data rows (| a | b |) that aren't header/separator
        if (
            in_concepts
            and line.startswith("|")
            and "---" not in line
            and "Page" not in line
        ):
            parts = [p.strip() for p in line.strip("|").split("|")]
            if len(parts) >= 2 and parts[0]:
                entries += 1
    return {"total": entries, "file_lines": len(lines)}


def count_log() -> dict:
    """Count ##-prefixed entries in wiki/log.md."""
    log = REPO / "wiki" / "log.md"
    if not log.is_file():
        return {"total": 0}

    lines = log.read_text(encoding="utf-8").splitlines()
    entries = [l for l in lines if l.strip().startswith("## ")]
    return {"total": len(entries), "file_lines": len(lines)}


def fmt_size(path: Path) -> str:
    size = path.stat().st_size
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.0f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def main():
    raw = count_raw_qa()
    concepts = count_wiki_concepts()
    db = count_db()
    index = count_index()
    log = count_log()

    print("=" * 48)
    print("  mem-weaver — Inventory Report")
    print("=" * 48)

    # raw/qa
    print(f"\n  raw/qa/")
    print(f"    Total QA files:         {raw['total']}")
    for date, cnt in raw.get("by_date", {}).items():
        print(f"      {date}:  {cnt} file(s)")

    # wiki/concepts
    print(f"\n  wiki/concepts/")
    print(f"    Concept pages:          {concepts}")
    concept_path = REPO / "wiki" / "concepts"
    if concept_path.is_dir():
        for f in sorted(concept_path.glob("*.md")):
            print(f"      {f.name}  ({fmt_size(f)})")

    # db
    print(f"\n  db/wiki.db")
    print(f"    Pages table:            {db.get('pages', 'N/A')}")
    print(f"    QA pairs table:         {db.get('qa_pairs', 'N/A')}")
    print_fmt_size(REPO / "db" / "wiki.db")

    # wiki/index.md
    print(f"\n  wiki/index.md")
    print(f"    Indexed page entries:   {index['total']}")
    print(f"    File size:              {fmt_size(REPO / 'wiki' / 'index.md')}")

    # wiki/log.md
    print(f"\n  wiki/log.md")
    print(f"    Log entries:            {log['total']}")
    print(f"    File size:              {fmt_size(REPO / 'wiki' / 'log.md')}")

    print()
    print(f"  Total records:           {raw['total'] + concepts + db.get('pages', 0) + db.get('qa_pairs', 0)}")
    print("=" * 48)


def print_fmt_size(path: Path):
    if path.is_file():
        print(f"    File size:              {fmt_size(path)}")


if __name__ == "__main__":
    main()
