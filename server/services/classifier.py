"""Agent-Skills topic routing: keyword match with Ollama fallback."""

import logging

from server.config import Settings
from server.ollama.client import ollama_generate_text

logger = logging.getLogger(__name__)

SKILL_TAXONOMY: dict[str, dict] = {
    "coding": {
        "keywords": [
            "python", "code", "function", "class", "api", "debug", "error",
            "import", "fastapi", "typescript", "async", "test", "deploy",
            "docker", "git", "bash", "script", "library", "package",
        ],
        "wiki_paths": [
            "coding/python-patterns",
            "coding/llm-integration",
            "coding/testing-strategy",
        ],
    },
    "design": {
        "keywords": [
            "architecture", "system", "design", "pattern", "microservice",
            "schema", "database", "endpoint", "structure", "flow", "diagram",
        ],
        "wiki_paths": ["design/system-architecture", "design/api-design"],
    },
    "ml": {
        "keywords": [
            "llm", "model", "rag", "embedding", "prompt", "token", "context",
            "fine-tune", "inference", "agent", "memory", "vector", "attention",
            "transformer", "ollama", "anthropic", "openai",
        ],
        "wiki_paths": [
            "ml/rag-patterns",
            "ml/memory-mechanisms",
            "ml/agent-skills",
        ],
    },
    "business": {
        "keywords": [
            "deadline", "client", "project", "budget", "meeting", "requirement",
            "stakeholder", "roadmap", "sprint", "feature", "cost", "roi",
        ],
        "wiki_paths": ["business/project-context"],
    },
    "general": {
        "keywords": [],  # fallback
        "wiki_paths": ["general/user-preferences"],
    },
}


def classify_topic(question: str) -> tuple[str, list[str]]:
    """Fast keyword-based classification. Returns (topic_name, wiki_slugs)."""
    q = question.lower()
    scores = {
        topic: sum(1 for kw in data["keywords"] if kw in q)
        for topic, data in SKILL_TAXONOMY.items()
    }
    best_topic = max(scores, key=scores.get)  # type: ignore[arg-type]
    if scores[best_topic] == 0:
        best_topic = "general"
    return best_topic, list(SKILL_TAXONOMY[best_topic]["wiki_paths"])


async def classify_with_ollama(
    question: str,
    settings: Settings,
) -> str:
    """Ollama fallback when keyword score is zero for all non-general topics."""
    try:
        result = await ollama_generate_text(
            settings.ollama_host,
            settings.ollama_model,
            (
                "Classify into ONE category: coding / design / ml / business / general\n"
                f'Question: "{question}"\n'
                "Reply with only the category word."
            ),
            timeout=30.0,
            api_key=settings.ollama_api_key,
        )
        result = result.strip().lower()
        if result in SKILL_TAXONOMY:
            return result
    except Exception:
        logger.exception("ollama classification fallback failed")
    return "general"
