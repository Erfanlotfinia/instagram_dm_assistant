from __future__ import annotations

import re
from typing import Any

SENSITIVE_KEYS = frozenset(
    {
        "password",
        "password_hash",
        "access_token",
        "access_token_encrypted",
        "token",
        "authorization",
        "secret",
        "jwt",
        "api_key",
        "openai_api_key",
        "gemini_api_key",
        "token_encryption_key",
        "jwt_secret_key",
        "email",
        "phone",
        "phone_number",
    }
)

BEARER_PATTERN = re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE)
JWT_PATTERN = re.compile(r"eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+")


def mask_string(value: str) -> str:
    masked = BEARER_PATTERN.sub("Bearer [REDACTED]", value)
    masked = JWT_PATTERN.sub("[REDACTED_JWT]", masked)
    return masked


def mask_value(key: str | None, value: Any) -> Any:
    if key and key.lower() in SENSITIVE_KEYS:
        return "[REDACTED]"
    if isinstance(value, str):
        return mask_string(value)
    if isinstance(value, dict):
        return mask_dict(value)
    if isinstance(value, list):
        return [mask_value(None, item) for item in value]
    return value


def mask_dict(data: dict[str, Any]) -> dict[str, Any]:
    return {key: mask_value(key, value) for key, value in data.items()}
