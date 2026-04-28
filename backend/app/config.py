"""Application configuration loaded from environment variables."""
from __future__ import annotations

from functools import lru_cache
from typing import List, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed settings sourced from .env / environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # LLM provider
    llm_provider: Literal["ollama", "groq"] = "ollama"

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"

    # Groq
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-8b-instant"

    # Vector store
    chroma_dir: str = "./chroma_db"
    chroma_collection: str = "support_kb"

    # Retrieval
    top_k: int = Field(default=4, ge=1, le=20)
    similarity_threshold: float = Field(default=0.3, ge=0.0, le=1.0)

    # Server
    allowed_origins: str = "http://localhost:5173"
    log_level: str = "INFO"

    @property
    def cors_origins(self) -> List[str]:
        """Parse comma-separated origins into a list."""
        if self.allowed_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @field_validator("groq_api_key")
    @classmethod
    def _strip_key(cls, v: str) -> str:
        return v.strip()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
