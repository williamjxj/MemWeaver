"""Ollama HTTP client."""

from server.ollama.client import ollama_generate, ollama_generate_json, ollama_generate_text

__all__ = ["ollama_generate", "ollama_generate_json", "ollama_generate_text"]
