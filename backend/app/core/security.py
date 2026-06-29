from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import bcrypt
import jwt
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings

_BCRYPT_ROUNDS = 12


def hash_secret(secret: str) -> str:
    return bcrypt.hashpw(
        secret.encode("utf-8"),
        bcrypt.gensalt(rounds=_BCRYPT_ROUNDS),
    ).decode("utf-8")


def verify_secret(secret: str, hashed_secret: str) -> bool:
    try:
        return bcrypt.checkpw(secret.encode("utf-8"), hashed_secret.encode("utf-8"))
    except (TypeError, ValueError):
        return False


def _fernet() -> Fernet:
    import base64
    import hashlib

    settings = get_settings()
    derived_key = base64.urlsafe_b64encode(
        hashlib.sha256(settings.token_encryption_key.encode("utf-8")).digest()
    )
    return Fernet(derived_key)


def encrypt_secret(secret: str) -> str:
    return _fernet().encrypt(secret.encode("utf-8")).decode("utf-8")


def decrypt_secret(encrypted_secret: str) -> str:
    try:
        return _fernet().decrypt(encrypted_secret.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Unable to decrypt secret") from exc


def create_access_token(subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    settings = get_settings()
    expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    now = datetime.now(UTC)
    payload: dict[str, Any] = {"sub": subject, "exp": expire, "iat": now, "jti": uuid4().hex}
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
