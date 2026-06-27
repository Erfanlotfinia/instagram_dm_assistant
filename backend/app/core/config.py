from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_env: Literal["local", "development", "staging", "production", "test"] = "local"
    log_level: str = "INFO"
    public_api_base_url: str = "http://localhost:8000"
    frontend_base_url: str = "http://localhost:5173"
    database_url: str = "postgresql+psycopg://postgres:postgres@postgres:5432/modira"
    redis_url: str = "redis://redis:6379/0"
    rabbitmq_url: str = "amqp://guest:guest@rabbitmq:5672/"
    qdrant_url: str = "http://qdrant:6333"
    llm_provider: Literal["openai", "gemini"] = Field(
        default="openai",
        description=(
            "LLM provider for chat extraction "
            "(openai = OpenAI-compatible API, gemini = Google Gemini)"
        ),
    )
    openai_api_key: str = ""
    openai_api_base_url: str = Field(
        default="https://api.avalai.ir/v1",
        description="OpenAI-compatible API base URL (AvalAI gateway by default)",
    )
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gemini_embedding_model: str = "gemini-embedding-001"
    qdrant_collection_name: str = "products"
    qdrant_variants_collection_name: str = "variants"
    catalog_import_batch_size: int = Field(default=25, ge=1)
    catalog_reindex_batch_size: int = Field(default=50, ge=1)
    resolver_default_high_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    resolver_default_medium_threshold: float = Field(default=0.55, ge=0.0, le=1.0)
    hybrid_fusion_strategy: str = "rrf"
    hybrid_rrf_k: int = Field(default=60, ge=1)
    agent_intent_confidence_threshold: float = 0.65
    agent_slots_confidence_threshold: float = 0.60
    agent_max_failures: int = 2
    jwt_secret_key: str = Field(default="change-me-in-production", min_length=16)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    auth_cookie_secure: bool | None = None
    csrf_cookie_name: str = "modira_csrf"
    token_encryption_key: str = Field(
        default="local-dev-token-encryption-key-32b!",
        min_length=32,
        description="Fernet-compatible key for encrypting channel access tokens",
    )
    cors_origins: list[str] = ["http://localhost:5173", "http://frontend:5173"]
    cors_allow_credentials: bool = True
    rate_limit_enabled: bool = True
    trusted_proxy_cidrs: list[str] = []
    rate_limit_login_per_minute: int = Field(default=10, ge=1)
    rate_limit_webhook_per_minute: int = Field(default=120, ge=1)
    rate_limit_outbound_message_per_minute: int = Field(default=30, ge=1)
    webhook_internal_secret: str = Field(
        default="",
        description="Secret used for webhook endpoint verification",
    )
    oauth_state_secret: str = Field(
        default="local-dev-oauth-state-secret",
        description="Secret used to sign provider OAuth state",
    )
    meta_app_id: str = ""
    meta_app_secret: str = Field(
        default="",
        description="Meta app secret for X-Hub-Signature-256 verification",
    )
    meta_graph_api_version: str = "v20.0"
    meta_graph_api_base_url: str = "https://graph.facebook.com"
    meta_oauth_scopes: list[str] = Field(
        default_factory=lambda: [
            "instagram_basic",
            "instagram_manage_messages",
            "pages_show_list",
            "pages_read_engagement",
            "pages_manage_metadata",
            "business_management",
        ]
    )
    meta_oauth_redirect_path: str = "/api/v1/channels/instagram/oauth/callback"
    meta_privacy_policy_url: str = ""
    enabled_channel_providers: str = "instagram,whatsapp,telegram,bale,rubika"
    enable_real_provider_send: bool = False
    conversation_lock_ttl_seconds: int = Field(default=120, ge=1)
    rabbitmq_queue_message_received: str = "channel.message.received"
    rabbitmq_queue_retry: str = "channel.message.received.retry"
    rabbitmq_queue_dlq: str = "channel.message.received.dlq"
    rabbitmq_queue_payment_callbacks: str = "payment_callbacks"
    rabbitmq_queue_reservation_expiry: str = "reservation_expiry"
    rabbitmq_queue_order_compensation: str = "order_compensation"
    rabbitmq_queue_operator_alerts: str = "operator_alerts"
    rabbitmq_queue_dead_letter: str = "dead_letter"
    reservation_default_ttl_seconds: int = Field(default=1800, ge=60)
    rabbitmq_max_retries: int = Field(default=3, ge=0)
    rabbitmq_retry_delay_ms: int = Field(default=30_000, ge=1000)
    order_expiration_minutes: int = Field(default=30, ge=1)
    background_job_interval_seconds: int = Field(default=60, ge=10)
    embedding_refresh_batch_size: int = Field(default=50, ge=1)
    default_model_version: str = "gpt-4o-mini"
    default_prompt_version: str = "trust-layer-v1"
    default_policy_version: str = "trust-layer-v1"
    llm_mode: Literal["mock", "live"] = "mock"
    webhook_signature_bypass: bool = Field(
        default=False,
        description="Development/test only: allow webhook POST without signature verification",
    )
    trl_live_llm_enabled: bool = Field(
        default=False,
        description="Enable live LLM mode for TRL validation runs (staging only)",
    )
    trl_average_processing_time_ms_threshold: int = Field(default=2000, ge=100)
    trl_p95_processing_time_ms_threshold: int = Field(default=5000, ge=100)
    default_admin_email: str = Field(
        default="admin@example.com",
        description="Email for the bootstrap admin created on startup (local/dev)",
    )
    default_admin_password: str = Field(
        default="changeme123",
        min_length=8,
        description="Password for the bootstrap admin created on startup (local/dev)",
    )
    default_admin_name: str = Field(
        default="Platform Admin",
        description="Display name for the bootstrap admin created on startup (local/dev)",
    )
    telegram_manager_bot_token: str = Field(
        default="",
        description="Platform Telegram manager bot token for managed bot provisioning",
    )
    telegram_manager_bot_username: str = Field(
        default="",
        description="Platform Telegram manager bot username (without @)",
    )
    telegram_manager_bot_id: str = Field(
        default="",
        description="Platform Telegram manager bot user id",
    )
    telegram_manager_webhook_secret: str = Field(
        default="",
        description="Secret token for verifying manager bot webhook requests",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


    @model_validator(mode="after")
    def validate_production_safety(self) -> "Settings":
        if self.app_env in {"staging", "production"}:
            default_jwt_values = {"change-me-in-production", "change-me-in-local-development"}
            default_token_values = {"local-dev-token-encryption-key-32b!"}
            if self.jwt_secret_key in default_jwt_values or len(self.jwt_secret_key) < 32:
                raise ValueError(
                    f"JWT_SECRET_KEY must be a strong non-default secret in {self.app_env}"
                )
            if (
                self.token_encryption_key in default_token_values
                or len(self.token_encryption_key) < 32
            ):
                raise ValueError(
                    f"TOKEN_ENCRYPTION_KEY must be a strong non-default secret in {self.app_env}"
                )
            enabled_providers = {
                provider.strip().lower()
                for provider in self.enabled_channel_providers.split(",")
                if provider.strip()
            }
            if (
                enabled_providers.intersection({"instagram", "whatsapp"})
                and not self.meta_app_secret
            ):
                raise ValueError(
                    f"META_APP_SECRET is required in {self.app_env} when Meta providers are enabled"
                )
            if "instagram" in enabled_providers and not self.meta_app_id:
                raise ValueError(
                    f"META_APP_ID is required in {self.app_env} when Instagram is enabled"
                )
            if not self.cors_origins or "*" in self.cors_origins:
                raise ValueError(f"CORS_ORIGINS must be explicit in {self.app_env}")
            if self.cors_allow_credentials and "*" in self.cors_origins:
                raise ValueError("CORS wildcard with credentials is not allowed")
            if "sqlite" in self.database_url.lower():
                raise ValueError(f"DATABASE_URL must not use SQLite in {self.app_env}")
            if self.app_env == "production" and any(
                origin.startswith("http://") for origin in self.cors_origins
            ):
                raise ValueError("CORS_ORIGINS must use HTTPS in production")
            if self.llm_mode == "live":
                if self.llm_provider == "gemini" and not self.gemini_api_key:
                    raise ValueError(
                        "GEMINI_API_KEY is required when "
                        "LLM_PROVIDER=gemini and LLM_MODE=live"
                    )
                if self.llm_provider == "openai" and not self.openai_api_key:
                    raise ValueError(
                        "OPENAI_API_KEY is required when "
                        "LLM_PROVIDER=openai and LLM_MODE=live"
                    )
            if self.webhook_signature_bypass:
                raise ValueError("WEBHOOK_SIGNATURE_BYPASS is not allowed in staging/production")
        return self

    @computed_field  # type: ignore[misc]
    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @computed_field  # type: ignore[misc]
    @property
    def chat_model(self) -> str:
        if self.llm_provider == "gemini":
            return self.gemini_model
        return self.openai_model

    @computed_field  # type: ignore[misc]
    @property
    def embedding_model(self) -> str:
        if self.llm_provider == "gemini":
            return self.gemini_embedding_model
        return self.openai_embedding_model

    @computed_field  # type: ignore[misc]
    @property
    def llm_api_key_configured(self) -> bool:
        if self.llm_provider == "gemini":
            return bool(self.gemini_api_key)
        return bool(self.openai_api_key)

    @computed_field  # type: ignore[misc]
    @property
    def meta_oauth_redirect_uri(self) -> str:
        return f"{self.public_api_base_url.rstrip('/')}{self.meta_oauth_redirect_path}"

    @computed_field  # type: ignore[misc]
    @property
    def requires_webhook_signature(self) -> bool:
        if self.app_env in {"staging", "production"}:
            return True
        return not self.webhook_signature_bypass


@lru_cache
def get_settings() -> Settings:
    return Settings()
