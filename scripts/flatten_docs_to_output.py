#!/usr/bin/env python3
"""Copy docs/**/*.md into output/ as a flat directory (no subfolders).

Each source file keeps a unique name derived from its path under docs/:
  docs/v1/s1-claude.md  ->  output/v1-s1-claude.md
  docs/prd.md           ->  output/prd.md

Does not modify docs/ or delete existing files in output/ (add/update only).

Usage:
    python scripts/flatten_docs_to_output.py
    python scripts/flatten_docs_to_output.py --docs-dir docs --output-dir output
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent


def flat_name(relative_md: Path) -> str:
    """Build a single-level filename from a path relative to docs/."""
    parts = relative_md.with_suffix("").parts
    return "-".join(parts) + ".md"


def flatten_docs(docs_dir: Path, output_dir: Path) -> list[tuple[Path, Path]]:
    """Copy every .md under docs_dir into output_dir. Returns (src, dst) pairs."""
    if not docs_dir.is_dir():
        raise FileNotFoundError(f"docs directory not found: {docs_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)

    copied: list[tuple[Path, Path]] = []
    seen_names: dict[str, Path] = {}

    for src in sorted(docs_dir.rglob("*.md")):
        if not src.is_file():
            continue

        relative = src.relative_to(docs_dir)
        name = flat_name(relative)
        if name in seen_names:
            prev = seen_names[name]
            raise ValueError(
                f"flatten name collision: {name}\n  {prev}\n  {src}"
            )

        seen_names[name] = src
        dst = output_dir / name
        shutil.copy2(src, dst)
        copied.append((src, dst))

    return copied


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Flatten docs/**/*.md into output/ (copy only)."
    )
    parser.add_argument(
        "--docs-dir",
        type=Path,
        default=_PROJECT_ROOT / "docs",
        help="Source tree (default: <repo>/docs)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=_PROJECT_ROOT / "output",
        help="Flat destination (default: <repo>/output)",
    )
    args = parser.parse_args(argv)

    docs_dir = args.docs_dir.resolve()
    output_dir = args.output_dir.resolve()

    try:
        copied = flatten_docs(docs_dir, output_dir)
    except (FileNotFoundError, ValueError) as err:
        print(f"error: {err}", file=sys.stderr)
        return 1

    print(f"Copied {len(copied)} file(s) from {docs_dir} -> {output_dir}")
    for src, dst in copied:
        rel = src.relative_to(docs_dir)
        print(f"  {rel} -> {dst.name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
