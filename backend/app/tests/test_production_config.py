import pytest

from app.core.config import Settings


def production_env(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("JWT_SECRET_KEY", "production-jwt-secret-key-32-characters-long")
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", "production-token-encryption-key-32-chars!")
    monkeypatch.setenv("CORS_ORIGINS", '["https://app.example.com"]')
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@db/modira")
    monkeypatch.setenv("ENABLED_CHANNEL_PROVIDERS", "telegram,bale,rubika")
    monkeypatch.setenv("WEBHOOK_SIGNATURE_BYPASS", "false")


def test_production_rejects_default_jwt_secret(monkeypatch) -> None:
    production_env(monkeypatch)
    monkeypatch.setenv("JWT_SECRET_KEY", "change-me-in-production")

    with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
        Settings()


def test_production_rejects_default_token_encryption_key(monkeypatch) -> None:
    production_env(monkeypatch)
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", "local-dev-token-encryption-key-32b!")

    with pytest.raises(ValueError, match="TOKEN_ENCRYPTION_KEY"):
        Settings()


def test_production_rejects_missing_token_encryption_key(monkeypatch) -> None:
    production_env(monkeypatch)
    monkeypatch.delenv("TOKEN_ENCRYPTION_KEY")

    with pytest.raises(ValueError, match="TOKEN_ENCRYPTION_KEY"):
        Settings()


def test_production_rejects_wildcard_cors(monkeypatch) -> None:
    production_env(monkeypatch)
    monkeypatch.setenv("CORS_ORIGINS", '["*"]')

    with pytest.raises(ValueError, match="CORS"):
        Settings()


def test_production_rejects_webhook_signature_bypass(monkeypatch) -> None:
    production_env(monkeypatch)
    monkeypatch.setenv("WEBHOOK_SIGNATURE_BYPASS", "true")

    with pytest.raises(ValueError, match="WEBHOOK_SIGNATURE_BYPASS"):
        Settings()


def test_production_does_not_require_instagram_env_for_non_meta_providers(monkeypatch) -> None:
    production_env(monkeypatch)

    settings = Settings()

    assert settings.enabled_channel_providers == "telegram,bale,rubika"
    assert settings.requires_webhook_signature is True


def test_production_requires_meta_secret_when_meta_provider_enabled(monkeypatch) -> None:
    production_env(monkeypatch)
    monkeypatch.setenv("ENABLED_CHANNEL_PROVIDERS", "instagram,telegram")
    monkeypatch.delenv("META_APP_SECRET", raising=False)

    with pytest.raises(ValueError, match="META_APP_SECRET"):
        Settings()


def test_queue_names_use_channel_generic_defaults(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")

    settings = Settings()

    assert settings.rabbitmq_queue_message_received == "channel.message.received"
    assert settings.rabbitmq_queue_retry == "channel.message.received.retry"
    assert settings.rabbitmq_queue_dlq == "channel.message.received.dlq"


def test_development_allows_local_defaults(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("JWT_SECRET_KEY", "change-me-in-local-development")

    settings = Settings()

    assert settings.app_env == "development"


def test_production_requires_gemini_key_when_live(monkeypatch) -> None:
    production_env(monkeypatch)
    monkeypatch.setenv("LLM_MODE", "live")
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "")

    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        Settings()
