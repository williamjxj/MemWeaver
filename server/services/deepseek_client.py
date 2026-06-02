"""Streaming DeepSeek client (OpenAI-compatible) for the /chat endpoint."""

import json
from typing import Any, AsyncGenerator

import httpx

from server.config import Settings

# Sentinel returned by _extract_token when the stream signals completion.
_DONE = object()


def _extract_token(line: str) -> Any:
    """Parse one OpenAI-style SSE line.

    Returns the content string, the _DONE sentinel on completion, or None
    for lines that carry no content (blank, comments, role-only deltas,
    or unparseable JSON).
    """
    line = line.strip()
    if not line or not line.startswith("data:"):
        return None
    payload = line[len("data:"):].strip()
    if payload == "[DONE]":
        return _DONE
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return None
    try:
        content = data["choices"][0]["delta"].get("content")
    except (KeyError, IndexError, TypeError):
        return None
    return content or None


async def stream_deepseek_chat(
    messages: list[dict[str, str]],
    settings: Settings,
) -> AsyncGenerator[str, None]:
    """Stream assistant text tokens from DeepSeek's chat-completions endpoint.

    POSTs directly to settings.deepseek_base_url (the full endpoint URL).
    """
    body = {
        "model": settings.deepseek_model,
        "messages": messages,
        "stream": True,
        "temperature": 0.2,
        "max_tokens": 256,
    }
    headers = {"Content-Type": "application/json"}
    if settings.deepseek_api_key:
        headers["Authorization"] = f"Bearer {settings.deepseek_api_key}"

    async with httpx.AsyncClient(timeout=settings.ollama_timeout) as client:
        async with client.stream(
            "POST", settings.deepseek_base_url, json=body, headers=headers
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                token = _extract_token(line)
                if token is _DONE:
                    return
                if token:
                    yield token
