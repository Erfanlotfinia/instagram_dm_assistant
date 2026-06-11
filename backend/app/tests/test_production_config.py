import pytest

from app.core.config import Settings


def test_production_rejects_default_jwt_secret(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("JWT_SECRET_KEY", "change-me-in-production")
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", "production-token-encryption-key-32-chars!")
    monkeypatch.setenv("INSTAGRAM_APP_SECRET", "prod-secret")
    monkeypatch.setenv("INSTAGRAM_WEBHOOK_VERIFY_TOKEN", "prod-verify-token")
    monkeypatch.setenv("CORS_ORIGINS", '["https://app.example.com"]')
    with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
        Settings()


def test_production_rejects_missing_instagram_secret(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("JWT_SECRET_KEY", "production-jwt-secret-key-32-characters-long")
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", "production-token-encryption-key-32-chars!")
    monkeypatch.setenv("INSTAGRAM_APP_SECRET", "")
    monkeypatch.setenv("INSTAGRAM_WEBHOOK_VERIFY_TOKEN", "prod-verify-token")
    monkeypatch.setenv("CORS_ORIGINS", '["https://app.example.com"]')
    with pytest.raises(ValueError, match="INSTAGRAM_APP_SECRET"):
        Settings()


def test_staging_rejects_wildcard_cors_with_credentials(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("JWT_SECRET_KEY", "staging-jwt-secret-key-32-characters-long!")
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", "staging-token-encryption-key-32-chars!")
    monkeypatch.setenv("INSTAGRAM_APP_SECRET", "staging-secret")
    monkeypatch.setenv("INSTAGRAM_WEBHOOK_VERIFY_TOKEN", "staging-verify-token")
    monkeypatch.setenv("CORS_ORIGINS", '["*"]')
    monkeypatch.setenv("CORS_ALLOW_CREDENTIALS", "true")
    with pytest.raises(ValueError, match="CORS"):
        Settings()


def test_development_allows_local_defaults(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("JWT_SECRET_KEY", "change-me-in-local-development")
    settings = Settings()
    assert settings.app_env == "development"


def test_webhook_signature_required_in_production(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("JWT_SECRET_KEY", "production-jwt-secret-key-32-characters-long")
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", "production-token-encryption-key-32-chars!")
    monkeypatch.setenv("INSTAGRAM_APP_SECRET", "prod-secret")
    monkeypatch.setenv("INSTAGRAM_WEBHOOK_VERIFY_TOKEN", "prod-verify-token")
    monkeypatch.setenv("CORS_ORIGINS", '["https://app.example.com"]')
    monkeypatch.delenv("WEBHOOK_SIGNATURE_BYPASS", raising=False)
    settings = Settings()
    assert settings.requires_webhook_signature is True
