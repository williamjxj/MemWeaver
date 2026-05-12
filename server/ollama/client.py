"""Async Ollama `/api/generate` wrapper with retries."""

import asyncio
import json
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


def _auth_headers(api_key: str) -> dict[str, str]:
    """Return headers dict with Bearer token when *api_key* is non-empty."""
    if api_key:
        return {"Authorization": f"Bearer {api_key}"}
    return {}


def _extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()

    # Strip markdown code fences (```json ... ```, ``` ... ```)
    if text.startswith("```"):
        first_nl = text.find("\n")
        if first_nl != -1:
            text = text[first_nl + 1 :].strip()
        for suffix in ("```", "``"):
            if text.endswith(suffix):
                text = text[: -len(suffix)].strip()
                break

    try:
        out = json.loads(text)
        if isinstance(out, dict):
            return out
    except json.JSONDecodeError:
        pass

    # Extract the first {…} block (handles preamble / postamble text)
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        candidate = text[start : end + 1]
        try:
            out = json.loads(candidate)
            if isinstance(out, dict):
                return out
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Model output is not a JSON object: {text[:300]}")


async def ollama_generate(
    base_url: str,
    model: str,
    prompt: str,
    *,
    timeout: float = 120.0,
    json_mode: bool = True,
    api_key: str = "",
) -> str:
    """
    Call Ollama generate API and return the `response` text (JSON string if json_mode).

    If *api_key* is provided it is sent as an ``Authorization: Bearer`` header
    (required for Ollama Cloud or any protected endpoint).
    """
    url = f"{base_url.rstrip('/')}/api/generate"
    body: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }
    if json_mode:
        body["format"] = "json"

    headers = _auth_headers(api_key)

    last_err: Exception | None = None
    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(3):
            try:
                r = await client.post(url, json=body, headers=headers)
                r.raise_for_status()
                data = r.json()
                return str(data.get("response", ""))
            except (httpx.TimeoutException, httpx.HTTPStatusError, httpx.RequestError) as e:
                last_err = e
                logger.warning("ollama attempt %s failed: %s", attempt + 1, e)
                await asyncio.sleep(2**attempt)
    assert last_err is not None
    raise last_err


async def ollama_generate_json(
    base_url: str,
    model: str,
    prompt: str,
    *,
    timeout: float = 120.0,
    api_key: str = "",
) -> dict[str, Any]:
    """Call Ollama with JSON format and parse the response string into a dict."""
    raw = await ollama_generate(base_url, model, prompt, timeout=timeout, json_mode=True, api_key=api_key)
    return _extract_json_object(raw)


async def ollama_generate_text(
    base_url: str,
    model: str,
    prompt: str,
    *,
    timeout: float = 120.0,
    api_key: str = "",
) -> str:
    """Call Ollama for free-form markdown text (no JSON `format` flag)."""
    text = await ollama_generate(base_url, model, prompt, timeout=timeout, json_mode=False, api_key=api_key)
    t = text.strip()
    if t.startswith("```"):
        lines = t.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        t = "\n".join(lines).strip()
    return t
