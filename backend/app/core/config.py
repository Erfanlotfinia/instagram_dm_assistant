from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_env: Literal["local", "development", "staging", "production", "test"] = "local"
    log_level: str = "INFO"
    database_url: str = "postgresql+psycopg://postgres:postgres@postgres:5432/instagram_dm_assistant"
    redis_url: str = "redis://redis:6379/0"
    rabbitmq_url: str = "amqp://guest:guest@rabbitmq:5672/"
    qdrant_url: str = "http://qdrant:6333"
    openai_api_key: str = ""
    jwt_secret_key: str = Field(default="change-me-in-production", min_length=16)
    cors_origins: list[str] = ["http://localhost:5173", "http://frontend:5173"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @computed_field  # type: ignore[misc]
    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
