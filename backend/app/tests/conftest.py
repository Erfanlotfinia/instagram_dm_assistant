import os
from collections.abc import Generator
from pathlib import Path
from urllib.parse import urlparse, urlunparse


def _resolve_test_database_url() -> str:
    explicit = os.getenv("TEST_DATABASE_URL")
    if explicit:
        return explicit

    source = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5432/instagram_dm_assistant",
    )
    parsed = urlparse(source)
    hostname = parsed.hostname or "localhost"
    if hostname in {"postgres", "db"} and not Path("/.dockerenv").exists():
        hostname = "localhost"

    username = parsed.username or "postgres"
    password = parsed.password or "postgres"
    port = parsed.port or 5432
    netloc = f"{username}:{password}@{hostname}:{port}"
    return urlunparse(parsed._replace(netloc=netloc, path="/instagram_dm_assistant_test"))


TEST_DATABASE_URL = _resolve_test_database_url()
os.environ["DATABASE_URL"] = TEST_DATABASE_URL


def _resolve_redis_url() -> str:
    explicit = os.getenv("TEST_REDIS_URL")
    if explicit:
        return explicit
    source = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    parsed = urlparse(source)
    if parsed.hostname == "redis" and not Path("/.dockerenv").exists():
        return "redis://localhost:6379/0"
    return source


os.environ["REDIS_URL"] = _resolve_redis_url()
os.environ["APP_ENV"] = "development"
os.environ["WEBHOOK_SIGNATURE_BYPASS"] = "true"
os.environ["LLM_MODE"] = "mock"
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

import app.domain  # noqa: F401
from app.db.session import get_db_session
from app.domain.enums import UserRole
from app.domain.models import Shop, ShopMember
from app.core.config import get_settings
from app.main import create_app
from app.services.auth_service import AuthService

get_settings.cache_clear()


def _bootstrap_test_schema() -> None:
    admin_engine = create_engine(
        TEST_DATABASE_URL,
        pool_pre_ping=True,
        isolation_level="AUTOCOMMIT",
    )
    with admin_engine.connect() as connection:
        connection.execute(text("SELECT pg_advisory_lock(9150242)"))
        try:
            connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
            connection.execute(text("CREATE SCHEMA public"))
            connection.execute(text("GRANT ALL ON SCHEMA public TO postgres"))
            connection.execute(text("GRANT ALL ON SCHEMA public TO public"))
        finally:
            connection.execute(text("SELECT pg_advisory_unlock(9150242)"))
    admin_engine.dispose()

    get_settings.cache_clear()
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    command.upgrade(alembic_cfg, "head")


@pytest.fixture(scope="session", autouse=True)
def _reset_redis_for_tests() -> Generator[None, None, None]:
    try:
        import redis

        client = redis.Redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
        client.flushdb()
    except Exception:
        pass
    yield


@pytest.fixture(autouse=True)
def _reset_request_context() -> Generator[None, None, None]:
    from app.core.request_context import clear_request_context

    clear_request_context()
    yield
    clear_request_context()


@pytest.fixture(autouse=True)
def _clear_webhook_idempotency_keys() -> Generator[None, None, None]:
    try:
        import redis

        client = redis.Redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
        for key in client.scan_iter("webhook:idem:*"):
            client.delete(key)
    except Exception:
        pass
    yield


@pytest.fixture(scope="session")
def engine():
    _bootstrap_test_schema()
    test_engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    yield test_engine
    with test_engine.begin() as connection:
        connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    test_engine.dispose()


@pytest.fixture()
def db_session(engine) -> Generator[Session, None, None]:
    """Per-test session with savepoints so service-layer commits stay isolated.

    Application code calls ``session.commit()`` frequently. Without savepoints each
    commit ends the outer test transaction, so later queries see no rows and teardown
    cannot roll back. ``join_transaction_mode='create_savepoint'`` maps commits to
    nested transactions that release on commit while the outer transaction rolls back
    at the end of the test.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(
        bind=connection,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )()
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def admin_user(db_session: Session):
    return AuthService.create_user(
        db_session,
        email="admin@test.com",
        password="password123",
        full_name="Test Admin",
        role=UserRole.OWNER,
    )


@pytest.fixture()
def auth_headers(client: TestClient, admin_user) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "password123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def order_product(db_session: Session, demo_shop):
    from decimal import Decimal

    from app.domain.models import Product, ProductVariant

    product = Product(
        shop_id=demo_shop.id,
        title="Order Test Product",
        base_price=Decimal("25.00"),
        currency="USD",
    )
    db_session.add(product)
    db_session.flush()
    variant = ProductVariant(
        product_id=product.id,
        sku="ORD-001",
        color="Red",
        size="M",
        price=Decimal("25.00"),
        stock_quantity=5,
        reserved_quantity=0,
    )
    db_session.add(variant)
    db_session.commit()
    db_session.refresh(product)
    db_session.refresh(variant)
    return {"product": product, "variant": variant}


@pytest.fixture()
def demo_shop(db_session: Session, admin_user):
    shop = Shop(name="Test Shop", slug="test-shop")
    db_session.add(shop)
    db_session.flush()
    db_session.add(
        ShopMember(
            shop_id=shop.id,
            user_id=admin_user.id,
            role=UserRole.OWNER,
        )
    )
    db_session.commit()
    db_session.refresh(shop)
    return shop
