"""
VERIFY-X 2.0 Backend Configuration

Loads all settings from environment variables with sensible defaults.
"""

from __future__ import annotations

from enum import Enum
from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class ModelMode(str, Enum):
    LOCAL = "local"
    REMOTE = "remote"


class LogFormat(str, Enum):
    JSON = "json"
    TEXT = "text"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ── Application ──
    app_name: str = "VERIFY-X"
    app_version: str = "2.0.0"
    debug: bool = False

    # ── Database ──
    database_url: str = "postgresql+asyncpg://verifyx:verifyx_dev@localhost:5432/verifyx"

    # ── Redis ──
    redis_url: str = "redis://localhost:6379/0"

    # ── API Keys ──
    news_api_key: Optional[str] = None
    hf_token: Optional[str] = None

    # ── Text Model ──
    text_base_model: str = "Qwen/Qwen3-8B"
    text_adapter: Optional[str] = None

    # ── Vision Model ──
    vision_base_model: str = "Qwen/Qwen2.5-VL-7B-Instruct"
    vision_adapter: Optional[str] = None

    # ── Model Mode ──
    model_mode: ModelMode = ModelMode.LOCAL

    # ── Embedding Model ──
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # ── MLflow ──
    mlflow_tracking_uri: str = "sqlite:///mlflow.db"

    # ── Security ──
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    rate_limit: str = "100/minute"
    max_upload_size_mb: int = 10

    # ── Logging ──
    log_level: str = "INFO"
    log_format: LogFormat = LogFormat.JSON

    # ── Cache TTL (seconds) ──
    cache_ttl_claims: int = 3600  # 1 hour
    cache_ttl_search: int = 1800  # 30 minutes
    cache_ttl_embeddings: int = 86400  # 24 hours

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str) -> str:
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()
