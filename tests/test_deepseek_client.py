"""Tests for the DeepSeek OpenAI-compatible SSE parser."""

from server.services.deepseek_client import _extract_token, _DONE


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
