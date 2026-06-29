import hashlib
import hmac
import json

from app.integrations.webhook_signature import verify_meta_signature
from app.tests.fixtures.instagram_webhook import SAMPLE_INSTAGRAM_MESSAGE_PAYLOAD


def test_meta_signature_verification() -> None:
    secret = "test-app-secret"
    body = json.dumps(SAMPLE_INSTAGRAM_MESSAGE_PAYLOAD).encode("utf-8")
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    assert verify_meta_signature(body, f"sha256={digest}", secret) is True
    assert verify_meta_signature(body, "sha256=invalid", secret) is False
    assert verify_meta_signature(body, None, secret) is False


def test_webhook_rejects_invalid_signature(client, demo_shop, db_session) -> None:
    from app.core.config import get_settings

    settings = get_settings()
    if not settings.meta_app_secret:
        return

    response = client.post(
        "/api/v1/channels/instagram/webhook",
        json=SAMPLE_INSTAGRAM_MESSAGE_PAYLOAD,
        headers={"X-Hub-Signature-256": "sha256=bad"},
    )
    assert response.status_code == 403
