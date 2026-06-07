import jwt
import pytest
from fastapi import HTTPException

from app.core.config import get_settings
from app.core.security import create_access_token, decrypt_secret, encrypt_secret, hash_secret, verify_secret
from app.domain.enums import UserRole
from app.schemas.auth import LoginRequest
from app.services.auth_service import AuthService


def test_password_hashing_roundtrip() -> None:
    hashed = hash_secret("password123")
    assert verify_secret("password123", hashed)
    assert not verify_secret("wrong-password", hashed)


def test_token_encryption_roundtrip() -> None:
    encrypted = encrypt_secret("instagram-access-token")
    assert decrypt_secret(encrypted) == "instagram-access-token"


def test_create_and_decode_access_token() -> None:
    token = create_access_token("user-id")
    settings = get_settings()
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    assert payload["sub"] == "user-id"


def test_authenticate_success(db_session, admin_user) -> None:
    service = AuthService(db_session)
    result = service.authenticate(LoginRequest(email="admin@test.com", password="password123"))
    assert result.access_token
    assert result.token_type == "bearer"


def test_authenticate_invalid_password(db_session, admin_user) -> None:
    service = AuthService(db_session)
    with pytest.raises(HTTPException) as exc_info:
        service.authenticate(LoginRequest(email="admin@test.com", password="wrong-password"))
    assert exc_info.value.status_code == 401


def test_get_user_from_token(db_session, admin_user) -> None:
    service = AuthService(db_session)
    token = create_access_token(str(admin_user.id))
    user = service.get_user_from_token(token)
    assert user.id == admin_user.id
    assert user.email == "admin@test.com"


def test_create_user(db_session) -> None:
    user = AuthService.create_user(
        db_session,
        email="new@test.com",
        password="password123",
        full_name="New User",
        role=UserRole.ADMIN,
    )
    assert user.email == "new@test.com"
    assert user.role == UserRole.ADMIN
