"""Tests for OpenAI-message construction in public_llm."""

from server.services.public_llm import (
    RECENT_HISTORY_TEMPLATE,
    RESPONSE_STYLE_TEMPLATE,
    WIKI_INJECTION_TEMPLATE,
    build_messages,
)


def test_build_messages_with_summary():
    msgs = build_messages("What is RAG?", "RAG = retrieval augmented generation")
    assert msgs[0]["role"] == "system"
    assert msgs[0]["content"] == RESPONSE_STYLE_TEMPLATE
    assert msgs[1]["role"] == "system"
    assert "RAG = retrieval augmented generation" in msgs[1]["content"]
    assert msgs[1]["content"] == WIKI_INJECTION_TEMPLATE.format(
        summary="RAG = retrieval augmented generation"
    )
    assert msgs[-1] == {"role": "user", "content": "What is RAG?"}
    assert len(msgs) == 3


def test_build_messages_without_summary():
    msgs = build_messages("Hello", "")
    assert msgs[0]["content"] == RESPONSE_STYLE_TEMPLATE
    assert msgs[-1] == {"role": "user", "content": "Hello"}


def test_build_messages_whitespace_summary_is_skipped():
    msgs = build_messages("Hello", "   \n  ")
    assert len(msgs) == 2
    assert msgs[0]["content"] == RESPONSE_STYLE_TEMPLATE
    assert msgs[1]["role"] == "user"


def test_build_messages_with_recent_history_and_summary():
    msgs = build_messages(
        "What should I do next?",
        "wiki memory",
        [
            {"role": "user", "content": "We discussed the roadmap."},
            {"role": "assistant", "content": "Use the API first."},
        ],
    )

    assert msgs[0]["role"] == "system"
    assert msgs[0]["content"] == RESPONSE_STYLE_TEMPLATE
    assert msgs[1]["role"] == "system"
    assert msgs[1]["content"] == RECENT_HISTORY_TEMPLATE.format(
        history="user: We discussed the roadmap.\nassistant: Use the API first."
    )
    assert msgs[2]["role"] == "system"
    assert msgs[2]["content"] == WIKI_INJECTION_TEMPLATE.format(summary="wiki memory")
    assert msgs[-1] == {"role": "user", "content": "What should I do next?"}


def test_build_messages_history_without_summary():
    msgs = build_messages(
        "Continue",
        "",
        [{"role": "user", "content": "Earlier question"}],
    )

    assert len(msgs) == 3
    assert msgs[0]["content"] == RESPONSE_STYLE_TEMPLATE
    assert msgs[1]["content"].startswith("You also have the most recent conversation turns")
    assert msgs[2] == {"role": "user", "content": "Continue"}


def test_build_messages_rich_history_adds_session_digest():
    history = [
        {"role": "user", "content": "We need to redesign the chat architecture"},
        {"role": "assistant", "content": "Keep QA, RAG, and wiki separate"},
        {"role": "user", "content": "Use session history to improve the QA prompt"},
        {"role": "assistant", "content": "Add a digest of recent decisions"},
        {"role": "user", "content": "Prefer a progressive memory layer"},
    ]

    msgs = build_messages("What should I do next?", "wiki memory", history)

    assert msgs[0]["role"] == "system"
    assert msgs[0]["content"] == RESPONSE_STYLE_TEMPLATE
    assert len(msgs) == 5
    assert msgs[1]["content"].startswith("You also have a compact session digest")
    assert msgs[1]["content"].startswith("You also have a compact session digest")
    assert "Focus terms:" in msgs[1]["content"]
    assert msgs[2]["content"] == RECENT_HISTORY_TEMPLATE.format(
        history="\n".join(
            [
                "user: We need to redesign the chat architecture",
                "assistant: Keep QA, RAG, and wiki separate",
                "user: Use session history to improve the QA prompt",
                "assistant: Add a digest of recent decisions",
                "user: Prefer a progressive memory layer",
            ]
        )
    )
    assert msgs[3]["content"] == WIKI_INJECTION_TEMPLATE.format(summary="wiki memory")
    assert msgs[-1] == {"role": "user", "content": "What should I do next?"}
