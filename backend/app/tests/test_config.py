from app.core.config import Settings


def test_settings_load_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/test_db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/1")
    monkeypatch.setenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    monkeypatch.setenv("QDRANT_URL", "http://localhost:6333")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-value")

    settings = Settings()

    assert settings.app_env == "test"
    assert settings.log_level == "DEBUG"
    assert settings.database_url.endswith("/test_db")
    assert settings.redis_url == "redis://localhost:6379/1"
    assert settings.rabbitmq_url.startswith("amqp://")
    assert settings.qdrant_url == "http://localhost:6333"
    assert settings.openai_api_key == "test-key"
    assert settings.jwt_secret_key == "test-secret-key-value"
    assert not settings.is_production
