from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed runtime settings for the API server and ingest pipeline."""

    app_name: str = "LLM-Wiki Middleware Delegator"
    app_env: str = "development"
    host: str = "127.0.0.1"
    port: int = 8000

    # Env: OLLAMA_HOST, OLLAMA_MODEL, OLLAMA_TIMEOUT, WIKI_DIR, RAW_DIR, DB_PATH, ...
    ollama_host: str = Field(default="http://127.0.0.1:11434")
    ollama_model: str = Field(default="minimax-m2.7:cloud")
    ollama_timeout: float = Field(default=120.0)

    wiki_dir: Path = Field(default=Path("wiki"))
    raw_dir: Path = Field(default=Path("raw/qa"))
    dlq_dir: Path = Field(default=Path("raw/failed"))
    db_path: Path = Field(default=Path("db/wiki.db"))

    max_queue_size: int = Field(default=100)
    max_atom_sentences: int = Field(default=3)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


def get_settings() -> Settings:
    return Settings()
