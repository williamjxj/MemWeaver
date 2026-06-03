"""Streaming DeepSeek client (OpenAI-compatible) for the /chat endpoint."""

import json
from typing import Any, AsyncGenerator

import httpx

from server.config import Settings

# Sentinel returned by _extract_token when the stream signals completion.
_DONE = object()


# Tunnel-vision tokens returned by _extract_token to distinguish content from
# reasoning — only the latter should be discarded if content ever appears.
_CONTENT = object()
_REASONING = object()


def _extract_token(line: str) -> tuple[Any, str] | Any:
    """Parse one OpenAI-style SSE line.

    Returns a 2-tuple (marker, token_text) for content-bearing lines:
      (_CONTENT,  text)  — a visible-response token (prefer this)
      (_REASONING, text) — an internal-reasoning token (fallback only)
    Returns _DONE on stream completion, or None for blank/ignorable lines.
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
        delta = data["choices"][0]["delta"]
    except (KeyError, IndexError, TypeError):
        return None

    content_text = delta.get("content")
    if content_text:
        return (_CONTENT, content_text)

    reasoning_text = delta.get("reasoning_content")
    if reasoning_text:
        return (_REASONING, reasoning_text)

    return None


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
        #         "max_tokens": 256,
    }
    headers = {"Content-Type": "application/json"}
    if settings.deepseek_api_key:
        headers["Authorization"] = f"Bearer {settings.deepseek_api_key}"

    async with httpx.AsyncClient(timeout=settings.ollama_timeout) as client:
        async with client.stream(
            "POST", settings.deepseek_base_url, json=body, headers=headers
        ) as response:
            response.raise_for_status()
            reasoning_buffer: list[str] = []
            content_seen = False
            async for line in response.aiter_lines():
                result = _extract_token(line)
                if result is _DONE:
                    if not content_seen and reasoning_buffer:
                        for token in reasoning_buffer:
                            yield token
                    return
                if result is None:
                    continue

                marker, text = result
                if marker is _CONTENT:
                    content_seen = True
                    reasoning_buffer.clear()
                    yield text
                elif marker is _REASONING and not content_seen:
                    reasoning_buffer.append(text)
