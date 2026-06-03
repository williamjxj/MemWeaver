"""Public-LLM chat streaming for /chat: builds OpenAI messages with wiki
context and delegates to the DeepSeek client."""

from collections import Counter
import re
from typing import AsyncGenerator

from server.config import Settings
from server.services.deepseek_client import stream_deepseek_chat

RESPONSE_STYLE_TEMPLATE = """\
Respond in a formal, professional, expert tone.
Start with the direct answer.
Keep the response brief and complete: 1-2 short paragraphs, or a concise summary plus at most 3 key points.
Do not say "Okay", "Sure", or similar filler.
Do not describe your process, steps, chain of thought, or internal reasoning.
Do not list intermediate actions or processing steps.
Never start your response with reasoning phrases like "We need to", "I should", "Let me", "First,", "Based on", or "The user".
Use plain text unless a compact list materially improves clarity.
If asked who you are (for example, "who are you", "what is your name"), reply exactly: "I am DeepSeek, an AI assistant."
If asked about your model version, your model name is {model_label}.
"""

WIKI_INJECTION_TEMPLATE = """\
You have structured background knowledge about this user and their projects. \
Use it as established context to give consistent, informed answers. \
Do not repeat this context back to the user.

--- Wiki Context ---
{summary}
---"""

RECENT_HISTORY_TEMPLATE = """\
You also have the most recent conversation turns. Use them to preserve local
continuity, resolve pronouns, and stay aligned with the user's evolving intent.
Do not repeat this transcript back to the user.

--- Recent Conversation ---
{history}
---"""

SESSION_DIGEST_TEMPLATE = """\
You also have a compact session digest from earlier turns. Use it to keep the
answer aligned with the user's longer-running goals, decisions, and open tasks.
Do not repeat this digest back to the user.

--- Session Digest ---
{digest}
---"""

_STOPWORDS = {
    "the",
    "and",
    "you",
    "for",
    "that",
    "this",
    "with",
    "have",
    "are",
    "was",
    "what",
    "when",
    "where",
    "why",
    "how",
    "can",
    "should",
    "could",
    "would",
    "about",
    "from",
    "into",
    "your",
    "their",
    "them",
    "been",
    "will",
    "just",
    "like",
    "want",
    "need",
    "please",
    "could",
    "more",
    "less",
    "here",
    "there",
    "after",
    "before",
    "over",
    "under",
}


def _format_recent_history(history: list[dict[str, str]], max_turns: int = 6) -> str:
    recent = history[-max_turns:]
    lines: list[str] = []
    for turn in recent:
        role = turn.get("role", "user")
        content = " ".join(turn.get("content", "").split())
        if not content:
            continue
        lines.append(f"{role}: {content[:500]}")
    return "\n".join(lines)


def _build_session_digest(history: list[dict[str, str]], max_items: int = 6) -> str:
    joined_turns = [" ".join(turn.get("content", "").split()) for turn in history]
    joined_text = " ".join(text for text in joined_turns if text)
    if not joined_text:
        return ""

    words = [word.lower() for word in re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", joined_text)]
    counts = Counter(word for word in words if word not in _STOPWORDS)
    focus_terms = [term for term, _ in counts.most_common(max_items)]

    user_turns = [
        " ".join(turn.get("content", "").split())
        for turn in history
        if turn.get("role") == "user" and turn.get("content", "").strip()
    ]
    assistant_turns = [
        " ".join(turn.get("content", "").split())
        for turn in history
        if turn.get("role") == "assistant" and turn.get("content", "").strip()
    ]

    lines: list[str] = []
    if focus_terms:
        lines.append(f"Focus terms: {', '.join(focus_terms[:5])}")
    if user_turns:
        recent_intent = " | ".join(user_turns[-2:])
        lines.append(f"Recent user intent: {recent_intent[:700]}")
    if assistant_turns:
        guidance = " | ".join(assistant_turns[-2:])
        lines.append(f"Recent assistant guidance: {guidance[:700]}")
    return "\n".join(lines)


def build_messages(
    question: str,
    wiki_summary: str = "",
    recent_history: list[dict[str, str]] | None = None,
    model_label: str = "DeepSeek",
) -> list[dict[str, str]]:
    """Build OpenAI chat messages. Wiki context becomes a system message
    (omitted when empty); recent conversation is injected when provided.

    Cold-start requests can pass no history and no wiki summary to send only
    the user question. As chat grows, the caller can provide both recent turns
    and distilled wiki context.
    """
    messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": RESPONSE_STYLE_TEMPLATE.format(model_label=model_label),
        }
    ]
    if recent_history:
        if len(recent_history) > 4:
            digest = _build_session_digest(recent_history)
            if digest:
                messages.append(
                    {
                        "role": "system",
                        "content": SESSION_DIGEST_TEMPLATE.format(digest=digest),
                    }
                )
        history_text = _format_recent_history(recent_history)
        if history_text:
            messages.append(
                {
                    "role": "system",
                    "content": RECENT_HISTORY_TEMPLATE.format(history=history_text),
                }
            )
    if wiki_summary.strip():
        messages.append(
            {
                "role": "system",
                "content": WIKI_INJECTION_TEMPLATE.format(summary=wiki_summary),
            }
        )
    messages.append({"role": "user", "content": question})
    return messages


async def stream_chat(
    messages: list[dict[str, str]],
    settings: Settings,
) -> AsyncGenerator[str, None]:
    """Stream DeepSeek tokens with the supplied OpenAI-style message list."""
    async for token in stream_deepseek_chat(messages, settings):
        yield token
