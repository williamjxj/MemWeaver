"""Slug and title helpers."""

import hashlib
import re


def slugify(text: str, max_len: int = 64) -> str:
    """URL-safe slug; falls back to short hash for non-ASCII or empty input."""
    s = text.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[-\s]+", "-", s).strip("-")
    if len(s) < 2:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    return s[:max_len]


def one_line(text: str, max_len: int = 120) -> str:
    line = " ".join(text.split())
    return line[:max_len] + ("…" if len(line) > max_len else "")
