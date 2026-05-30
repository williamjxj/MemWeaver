"""Optional LLM pass to prepend a contradiction warning to a wiki draft body."""

from __future__ import annotations

import json
import re
import logging
from typing import Any

from server.config import Settings
from server.ollama.client import ollama_generate
from server.pipeline.prompts import CONTRADICTION_CHECK_PROMPT

logger = logging.getLogger(__name__)

_CONTRADICTS_RE = re.compile(r'"contradicts"\s*:\s*(true|false)', re.IGNORECASE)
_NOTE_RE = re.compile(r'"note"\s*:\s*"((?:\\.|[^"\\])*)"', re.IGNORECASE | re.DOTALL)


def _parse_contradiction_result(raw: str) -> dict[str, Any]:
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    contradicts_match = _CONTRADICTS_RE.search(raw)
    if not contradicts_match:
        return {"contradicts": False, "note": ""}

    note_match = _NOTE_RE.search(raw)
    note = ""
    if note_match:
        note = bytes(note_match.group(1), "utf-8").decode("unicode_escape")

    return {
        "contradicts": contradicts_match.group(1).lower() == "true",
        "note": note,
    }


async def maybe_prepend_contradiction_block(
    settings: Settings,
    existing_body: str,
    atom: str,
    key_claims: list[str],
    draft_body: str,
) -> str:
    """If the page already has substantive content, ask Ollama whether the new atom contradicts it."""
    if not settings.enable_contradiction_check:
        return draft_body

    excerpt = (existing_body or "").strip()
    if len(excerpt) < 40:
        return draft_body
    try:
        raw = await ollama_generate(
            settings.ollama_host,
            settings.ollama_model,
            CONTRADICTION_CHECK_PROMPT.format(
                existing_excerpt=excerpt[:6000],
                atom=atom,
                key_claims_json=json.dumps(key_claims, ensure_ascii=False),
            ),
            timeout=min(60.0, settings.ollama_timeout),
        )
        data = _parse_contradiction_result(raw)
    except Exception:
        logger.warning("contradiction check failed; using draft without prepend")
        return draft_body
    if not data.get("contradicts"):
        return draft_body
    note = str(data.get("note") or "Possible conflict with existing page.").strip()
    prefix = f"> ⚠️ Contradiction noted: {note}\n\n"
    return prefix + draft_body
