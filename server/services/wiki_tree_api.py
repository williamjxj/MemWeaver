"""Build a sidebar-friendly wiki tree from `wiki/index.md`."""

from __future__ import annotations

import re
from pathlib import Path

from server.config import Settings

_CONCEPT_LINK = re.compile(r"\[\[([^\]|#]+)(?:\|[^\]]+)?\]\]")
_AUTO_INDEX_LINK = re.compile(r"-\s+\[\[([^\]|#]+)(?:\|[^\]]+)?\]\]")
_FRONTMATTER_TITLE = re.compile(r'^title:\s*"?(.*?)"?\s*$')


def _read_page_title(wiki_dir: Path, slug: str) -> str:
    page_path = wiki_dir / f"{slug}.md"
    if not page_path.exists():
        return slug.replace("-", " ").strip().title() or slug

    text = page_path.read_text(encoding="utf-8")
    if text.startswith("---"):
        frontmatter = text.split("---", 2)
        if len(frontmatter) >= 2:
            for line in frontmatter[1].splitlines():
                match = _FRONTMATTER_TITLE.match(line.strip())
                if match and match.group(1).strip():
                    return match.group(1).strip().strip('"')

    first_heading = next((line[2:].strip() for line in text.splitlines() if line.startswith("# ")), "")
    if first_heading:
        return first_heading

    return slug.replace("-", " ").strip().title() or slug


def _page_node(wiki_dir: Path, slug: str) -> dict[str, object]:
    return {
        "id": slug,
        "label": _read_page_title(wiki_dir, slug),
        "type": "page",
    }


def _section_from_index(wiki_dir: Path, index_text: str, section_name: str) -> list[dict[str, object]]:
    section_pattern = re.compile(rf"^##\s+{re.escape(section_name)}\s*$", re.IGNORECASE | re.MULTILINE)
    match = section_pattern.search(index_text)
    if not match:
        return []

    start = match.end()
    next_heading = re.search(r"^##\s+", index_text[start:], re.MULTILINE)
    end = start + next_heading.start() if next_heading else len(index_text)
    section_text = index_text[start:end]

    links: list[dict[str, object]] = []
    seen: set[str] = set()
    if section_name.lower() == "concepts":
        for line in section_text.splitlines():
            link_match = _CONCEPT_LINK.search(line)
            if link_match:
                slug = link_match.group(1).strip()
                if slug and slug not in seen:
                    seen.add(slug)
                    links.append(_page_node(wiki_dir, slug))
    elif section_name.lower() == "auto-index (pipeline)":
        for line in section_text.splitlines():
            link_match = _AUTO_INDEX_LINK.search(line)
            if link_match:
                slug = link_match.group(1).strip()
                if slug and slug not in seen:
                    seen.add(slug)
                    links.append(_page_node(wiki_dir, slug))
    return links


async def get_wiki_tree(settings: Settings) -> dict:
    """Return sidebar tree nodes grouped by wiki index sections."""
    index_path = settings.wiki_dir / "index.md"
    if not index_path.exists():
        return {"tree": []}

    index_text = index_path.read_text(encoding="utf-8")
    tree: list[dict[str, object]] = []

    concepts = _section_from_index(settings.wiki_dir, index_text, "Concepts")
    if concepts:
        tree.append({"id": "concepts", "label": "Concepts", "type": "folder", "children": concepts})

    auto_index = _section_from_index(settings.wiki_dir, index_text, "Auto-index (pipeline)")
    if auto_index:
        tree.append({"id": "auto-index", "label": "Auto-index", "type": "folder", "children": auto_index})

    return {"tree": tree}