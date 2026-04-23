"""Optional LLM pass to prepend a contradiction warning to a wiki draft body."""

from __future__ import annotations

import json
import logging
from typing import Any

from server.config import Settings
from server.ollama.client import ollama_generate_json
from server.pipeline.prompts import CONTRADICTION_CHECK_PROMPT

logger = logging.getLogger(__name__)


async def maybe_prepend_contradiction_block(
    settings: Settings,
    existing_body: str,
    atom: str,
    key_claims: list[str],
    draft_body: str,
) -> str:
    """If the page already has substantive content, ask Ollama whether the new atom contradicts it."""
    excerpt = (existing_body or "").strip()
    if len(excerpt) < 40:
        return draft_body
    try:
        data: dict[str, Any] = await ollama_generate_json(
            settings.ollama_host,
            settings.ollama_model,
            CONTRADICTION_CHECK_PROMPT.format(
                existing_excerpt=excerpt[:6000],
                atom=atom,
                key_claims_json=json.dumps(key_claims, ensure_ascii=False),
            ),
            timeout=min(60.0, settings.ollama_timeout),
        )
    except Exception:
        logger.exception("contradiction check failed; using draft without prepend")
        return draft_body
    if not data.get("contradicts"):
        return draft_body
    note = str(data.get("note") or "Possible conflict with existing page.").strip()
    prefix = f"> ⚠️ Contradiction noted: {note}\n\n"
    return prefix + draft_body
