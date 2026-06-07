from __future__ import annotations

import hashlib
import hmac


def verify_meta_signature(payload: bytes, signature_header: str | None, app_secret: str) -> bool:
    """Verify Meta X-Hub-Signature-256 header."""
    if not app_secret or not signature_header:
        return False
    if not signature_header.startswith("sha256="):
        return False
    expected = signature_header.removeprefix("sha256=")
    digest = hmac.new(app_secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, expected)
