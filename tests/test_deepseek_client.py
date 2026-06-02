"""Tests for the DeepSeek OpenAI-compatible SSE parser."""

import httpx
import pytest

from server.config import Settings
from server.services import deepseek_client
from server.services.deepseek_client import _extract_token, _DONE, stream_deepseek_chat


def test_extract_content_token():
    line = 'data: {"choices":[{"delta":{"content":"Hello"}}]}'
    assert _extract_token(line) == "Hello"


def test_extract_done_sentinel():
    assert _extract_token("data: [DONE]") is _DONE


def test_extract_blank_line_returns_none():
    assert _extract_token("") is None
    assert _extract_token("   ") is None


def test_extract_keepalive_or_role_chunk_returns_none():
    # role-only delta (first chunk) has no content
    line = 'data: {"choices":[{"delta":{"role":"assistant"}}]}'
    assert _extract_token(line) is None


def test_extract_non_data_line_returns_none():
    assert _extract_token(": keep-alive") is None


def test_extract_malformed_json_returns_none():
    assert _extract_token("data: {not json}") is None


@pytest.mark.asyncio
async def test_stream_deepseek_chat_yields_tokens_until_done(monkeypatch):
    sse_body = (
        'data: {"choices":[{"delta":{"role":"assistant"}}]}\n\n'
        'data: {"choices":[{"delta":{"content":"Hel"}}]}\n\n'
        ': keep-alive\n\n'
        'data: {"choices":[{"delta":{"content":"lo"}}]}\n\n'
        'data: [DONE]\n\n'
        'data: {"choices":[{"delta":{"content":"AFTER_DONE"}}]}\n\n'
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=sse_body)

    transport = httpx.MockTransport(handler)
    real_async_client = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        kwargs.pop("transport", None)
        return real_async_client(*args, transport=transport, **kwargs)

    monkeypatch.setattr(deepseek_client.httpx, "AsyncClient", client_factory)

    settings = Settings(deepseek_api_key="sk-test")
    tokens = [
        tok async for tok in stream_deepseek_chat(
            [{"role": "user", "content": "hi"}], settings
        )
    ]
    assert tokens == ["Hel", "lo"]


@pytest.mark.asyncio
async def test_stream_deepseek_chat_raises_on_http_error(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="unauthorized")

    transport = httpx.MockTransport(handler)
    real_async_client = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        kwargs.pop("transport", None)
        return real_async_client(*args, transport=transport, **kwargs)

    monkeypatch.setattr(deepseek_client.httpx, "AsyncClient", client_factory)

    settings = Settings(deepseek_api_key="sk-test")
    with pytest.raises(httpx.HTTPStatusError):
        async for _ in stream_deepseek_chat(
            [{"role": "user", "content": "hi"}], settings
        ):
            pass
