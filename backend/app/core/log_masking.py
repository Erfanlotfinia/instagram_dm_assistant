from __future__ import annotations

import hashlib
import hmac
import re
from collections.abc import Mapping, Sequence
from typing import Any

REDACTED = "[REDACTED]"

SENSITIVE_KEYS = frozenset(
    {
        "access_token",
        "access_token_encrypted",
        "refresh_token",
        "refresh_token_encrypted",
        "bot_token",
        "bot_token_encrypted",
        "webhook_secret",
        "webhook_secret_encrypted",
        "webhook_verify_token",
        "authorization",
        "cookie",
        "password",
        "password_hash",
        "api_key",
        "openai_api_key",
        "gemini_api_key",
        "jwt",
        "email",
        "phone",
        "phone_number",
        "address",
        "postal_code",
        "customer_id",
        "customer_identifier",
        "external_customer_id",
        "customer_external_id",
        "wa_id",
        "from",
        "token",
        "secret",
        "token_encryption_key",
        "jwt_secret_key",
        "payment",
        "card",
    }
)

BEARER_PATTERN = re.compile(r"Bearer\s+\S+", re.IGNORECASE)
AUTH_HEADER_PATTERN = re.compile(r"\b(authorization|cookie)\s*[:=]\s*[^,\n]+", re.IGNORECASE)
JWT_PATTERN = re.compile(r"eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+")
EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_PATTERN = re.compile(r"(?<!\w)\+?\d[\d\s().-]{6,}\d(?!\w)")


def normalize_key(key: str) -> str:
    return key.strip().lower().replace("-", "_")


def is_sensitive_key(key: str | None) -> bool:
    return bool(key and normalize_key(key) in SENSITIVE_KEYS)


def _mask_header_match(match: re.Match[str]) -> str:
    label = match.group(1)
    separator = ":" if ":" in match.group(0) else "="
    return f"{label}{separator} {REDACTED}"


def mask_string(value: str) -> str:
    masked = AUTH_HEADER_PATTERN.sub(_mask_header_match, value)
    masked = BEARER_PATTERN.sub("Bearer [REDACTED]", masked)
    masked = JWT_PATTERN.sub(REDACTED, masked)
    masked = EMAIL_PATTERN.sub(REDACTED, masked)
    masked = PHONE_PATTERN.sub(REDACTED, masked)
    return masked


def redact_value(value: Any, key: str | None = None) -> Any:
    if is_sensitive_key(key):
        return REDACTED
    if isinstance(value, str):
        return mask_string(value)
    if isinstance(value, Mapping):
        return {
            item_key: redact_value(item_value, str(item_key))
            for item_key, item_value in value.items()
        }
    if isinstance(value, tuple):
        return [redact_value(item) for item in value]
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [redact_value(item) for item in value]
    return value


def redact_dict(data: Mapping[str, Any]) -> dict[str, Any]:
    return {key: redact_value(value, key) for key, value in data.items()}


def stable_hash_identifier(value: Any, *, salt: str = "") -> str:
    raw = "" if value is None else str(value)
    digest = hmac.new(salt.encode(), raw.encode(), hashlib.sha256).hexdigest()
    return f"sha256:{digest}"


# Backwards-compatible aliases used by existing logging and response code.
def mask_value(key: str | None, value: Any) -> Any:
    return redact_value(value, key)


def mask_dict(data: dict[str, Any]) -> dict[str, Any]:
    return redact_dict(data)
