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
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    qdrant_collection_name: str = "products"
    agent_intent_confidence_threshold: float = 0.65
    agent_slots_confidence_threshold: float = 0.60
    agent_max_failures: int = 2
    jwt_secret_key: str = Field(default="change-me-in-production", min_length=16)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    token_encryption_key: str = Field(
        default="local-dev-token-encryption-key-32b!",
        min_length=32,
        description="Fernet-compatible key for encrypting Instagram access tokens",
    )
    cors_origins: list[str] = ["http://localhost:5173", "http://frontend:5173"]
    cors_allow_credentials: bool = True
    rate_limit_enabled: bool = True
    rate_limit_login_per_minute: int = Field(default=10, ge=1)
    rate_limit_webhook_per_minute: int = Field(default=120, ge=1)
    rate_limit_outbound_message_per_minute: int = Field(default=30, ge=1)
    instagram_app_secret: str = Field(
        default="",
        description="Meta app secret for X-Hub-Signature-256 verification (empty disables check)",
    )
    instagram_webhook_verify_token: str = Field(
        default="local-instagram-verify-token",
        description="Meta webhook verify token (VERIFY_TOKEN)",
    )
    enable_real_instagram_send: bool = False
    conversation_lock_ttl_seconds: int = Field(default=120, ge=1)
    rabbitmq_queue_message_received: str = "instagram.message.received"
    rabbitmq_queue_retry: str = "instagram.message.received.retry"
    rabbitmq_queue_dlq: str = "instagram.message.received.dlq"
    rabbitmq_queue_payment_callbacks: str = "payment_callbacks"
    rabbitmq_queue_reservation_expiry: str = "reservation_expiry"
    rabbitmq_queue_order_compensation: str = "order_compensation"
    rabbitmq_queue_operator_alerts: str = "operator_alerts"
    rabbitmq_queue_dead_letter: str = "dead_letter"
    reservation_default_ttl_seconds: int = Field(default=1800, ge=60)
    rabbitmq_max_retries: int = Field(default=3, ge=0)
    rabbitmq_retry_delay_ms: int = Field(default=30_000, ge=1000)
    api_public_base_url: str = "http://localhost:8000"
    order_expiration_minutes: int = Field(default=30, ge=1)
    background_job_interval_seconds: int = Field(default=60, ge=10)
    embedding_refresh_batch_size: int = Field(default=50, ge=1)

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
