import os
from collections.abc import Generator

os.environ.setdefault("RATE_LIMIT_ENABLED", "false")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

import app.domain  # noqa: F401
from app.db.base import Base
from app.db.session import get_db_session
from app.domain.enums import UserRole
from app.domain.models import Shop, ShopMember
from app.main import create_app
from app.services.auth_service import AuthService

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/instagram_dm_assistant_test",
)


@pytest.fixture(scope="session")
def engine():
    test_engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    with test_engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield test_engine
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture()
def db_session(engine) -> Generator[Session, None, None]:
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection, autocommit=False, autoflush=False)()
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
