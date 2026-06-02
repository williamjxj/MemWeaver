"""Tests for OpenAI-message construction in public_llm."""

from server.services.public_llm import build_messages, WIKI_INJECTION_TEMPLATE


def test_build_messages_with_summary():
    msgs = build_messages("What is RAG?", "RAG = retrieval augmented generation")
    assert msgs[0]["role"] == "system"
    assert "RAG = retrieval augmented generation" in msgs[0]["content"]
    assert msgs[-1] == {"role": "user", "content": "What is RAG?"}
    assert len(msgs) == 2


def test_build_messages_without_summary():
    msgs = build_messages("Hello", "")
    assert msgs == [{"role": "user", "content": "Hello"}]


def test_build_messages_whitespace_summary_is_skipped():
    msgs = build_messages("Hello", "   \n  ")
    assert len(msgs) == 1
    assert msgs[0]["role"] == "user"
