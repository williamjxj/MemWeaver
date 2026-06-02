"""Public-LLM chat streaming for /chat: builds OpenAI messages with wiki
context and delegates to the DeepSeek client."""

from typing import AsyncGenerator

from server.config import Settings
from server.services.deepseek_client import stream_deepseek_chat

WIKI_INJECTION_TEMPLATE = """\
You have structured background knowledge about this user and their projects. \
Use it as established context to give consistent, informed answers. \
Do not repeat this context back to the user.

--- Wiki Context ---
{summary}
---"""


def build_messages(question: str, wiki_summary: str) -> list[dict[str, str]]:
    """Build OpenAI chat messages. Wiki context becomes a system message
    (omitted when empty); the question is the user message."""
    messages: list[dict[str, str]] = []
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
    question: str,
    wiki_summary: str,
    settings: Settings,
) -> AsyncGenerator[str, None]:
    """Stream DeepSeek tokens with wiki context injected as a system message."""
    messages = build_messages(question, wiki_summary)
    async for token in stream_deepseek_chat(messages, settings):
        yield token
