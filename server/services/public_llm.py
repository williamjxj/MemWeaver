"""Streaming Ollama client for the /chat endpoint with wiki context injection."""

import json
import logging
from typing import AsyncGenerator

import httpx

from server.config import Settings

logger = logging.getLogger(__name__)

WIKI_INJECTION_TEMPLATE = """\
You have structured background knowledge about this user and their projects. \
Use it as established context to give consistent, informed answers. \
Do not repeat this context back to the user.

--- Wiki Context ---
{summary}
---"""


async def stream_ollama_chat(
    question: str,
    wiki_summary: str,
    settings: Settings,
) -> AsyncGenerator[str, None]:
    """Stream Ollama tokens with wiki context injected as a system-like priming message.

    Yields individual text tokens as they arrive from Ollama's streaming API.
    """
    if wiki_summary.strip():
        full_prompt = (
            f"{WIKI_INJECTION_TEMPLATE.format(summary=wiki_summary)}\n\n"
            f"User question: {question}"
        )
    else:
        full_prompt = question

    url = f"{settings.ollama_host.rstrip('/')}/api/generate"
    body = {
        "model": settings.ollama_model,
        "prompt": full_prompt,
        "stream": True,
    }

    headers = {}
    if settings.ollama_api_key:
        headers["Authorization"] = f"Bearer {settings.ollama_api_key}"

    async with httpx.AsyncClient(timeout=settings.ollama_timeout) as client:
        async with client.stream("POST", url, json=body, headers=headers) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    token = data.get("response", "")
                    if token:
                        yield token
                    if data.get("done", False):
                        return
                except json.JSONDecodeError:
                    logger.warning("skipping unparseable Ollama stream line: %s", line[:80])
