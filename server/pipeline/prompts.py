"""Ollama prompts aligned with docs/s2-claude-plan.md §6."""

SUMMARIZE_PROMPT = """\
You are a knowledge distiller. Given a Q/A pair from a chat session, extract the core knowledge atom.

Rules:
- Output exactly 1-3 sentences for "atom". No filler, no hedging.
- Extract only verifiable claims, not opinions.
- Identify 2-5 topic tags (lowercase, hyphenated).
- Identify any named entities (people, tools, systems).
- Return JSON only. No markdown. No preamble.

Output schema:
{{
  "atom": "<1-3 sentence distilled claim>",
  "key_claims": ["<claim 1>", "<claim 2>"],
  "detected_topics": ["<tag1>", "<tag2>"],
  "detected_entities": ["<EntityName>"]
}}

Q: {question}
A: {answer}
"""


WIKI_PAGE_PROMPT = """\
You maintain markdown wiki pages (Obsidian-style). Update the page body given a new atom.

Rules:
- Output **markdown body only** (no YAML frontmatter, no code fences wrapping the whole page).
- Use clear ## headings. Integrate new facts; keep prior structure where sensible.
- If a contradiction with existing text is obvious, append a blockquote line starting with "> Contradiction noted:" explaining briefly.
- Prefer short paragraphs and bullet lists for claims.

Existing page body (or the word EMPTY if new page):
{existing}

New atom:
{atom}

Key claims (bullets to weave in):
{claims}
"""
