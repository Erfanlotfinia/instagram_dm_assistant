from __future__ import annotations

from sqlalchemy import select

from app.core.log_masking import REDACTED, redact_value, stable_hash_identifier
from app.domain.enums import FailedJobStatus, TraceEventType, WebhookProvider
from app.domain.models import AdminAuditLog, FailedJob, TraceEvent, WebhookEvent
from app.services.audit_service import AuditService
from app.services.decision_trace_service import DecisionTraceService
from app.services.failed_job_service import FailedJobService
from app.services.webhook_ingestion_service import WebhookIngestionService


def _serialized(value: object) -> str:
    return str(value)


def test_central_redaction_masks_required_keys_and_patterns() -> None:
    payload = {
        "headers": {
            "Authorization": "Bearer provider-secret-jwt",
            "Cookie": "sessionid=raw-cookie; csrftoken=raw-csrf",
        },
        "access_token": "provider-access-token",
        "webhook_secret": "provider-webhook-secret",
        "profile": {
            "email": "customer@example.com",
            "phone": "+1 (415) 555-2671",
            "address": "123 Main St",
            "postal_code": "94105",
        },
        "notes": ["email customer@example.com", "call +1 415 555 2671"],
    }

    redacted = redact_value(payload)

    assert isinstance(redacted, dict)
    assert isinstance(redacted["notes"], list)
    assert redacted["headers"]["Authorization"] == REDACTED
    assert redacted["headers"]["Cookie"] == REDACTED
    assert redacted["access_token"] == REDACTED
    assert redacted["webhook_secret"] == REDACTED
    assert redacted["profile"]["email"] == REDACTED
    assert redacted["profile"]["phone"] == REDACTED
    serialized = _serialized(redacted)
    assert "customer@example.com" not in serialized
    assert "415" not in serialized
    assert "provider-access-token" not in serialized
    assert "provider-webhook-secret" not in serialized


def test_stable_hash_identifier_groups_without_raw_identifier() -> None:
    first = stable_hash_identifier("customer@example.com", salt="analytics")
    second = stable_hash_identifier("customer@example.com", salt="analytics")

    assert first == second
    assert first.startswith("sha256:")
    assert "customer@example.com" not in first


def test_failed_job_record_failure_persists_redacted_payload(db_session, demo_shop) -> None:
    job = FailedJobService.record_failure(
        db_session,
        queue_name="channel.message.received",
        job_type="message_received",
        payload={
            "shop_id": str(demo_shop.id),
            "access_token": "provider-access-token",
            "headers": {"authorization": "Bearer raw-auth", "cookie": "sid=raw-cookie"},
            "customer": {"email": "customer@example.com", "phone": "+14155552671"},
        },
        error_message="boom",
    )

    persisted = db_session.get(FailedJob, job.id)
    assert persisted is not None
    serialized = _serialized(persisted.payload)
    assert "provider-access-token" not in serialized
    assert "raw-auth" not in serialized
    assert "raw-cookie" not in serialized
    assert "customer@example.com" not in serialized
    assert "+14155552671" not in serialized
    assert persisted.payload["access_token"] == REDACTED
    assert persisted.status == FailedJobStatus.FAILED


def test_audit_metadata_is_redacted(db_session, demo_shop, admin_user) -> None:
    entry = AuditService(db_session).log(
        action="settings_updated",
        entity_type="shop",
        shop_id=demo_shop.id,
        actor_user_id=admin_user.id,
        metadata={
            "webhook_secret": "provider-webhook-secret",
            "email": "customer@example.com",
            "headers": {"authorization": "Bearer raw-auth", "cookie": "sid=raw-cookie"},
        },
    )
    db_session.commit()

    persisted = db_session.get(AdminAuditLog, entry.id)
    assert persisted is not None
    serialized = _serialized(persisted.details)
    assert "provider-webhook-secret" not in serialized
    assert "customer@example.com" not in serialized
    assert "raw-auth" not in serialized
    assert "raw-cookie" not in serialized


def test_decision_trace_event_payload_is_redacted(db_session, demo_shop) -> None:
    trace_id = DecisionTraceService.new_trace_id()
    event = DecisionTraceService(db_session).record(
        trace_id=trace_id,
        shop_id=demo_shop.id,
        event_type=TraceEventType.SLOTS_EXTRACTED,
        payload={
            "slots": {
                "phone": "+14155552671",
                "email": "customer@example.com",
                "address": "123 Main St",
            },
            "headers": {"authorization": "Bearer raw-auth", "cookie": "sid=raw-cookie"},
        },
        commit=True,
    )

    persisted = db_session.get(TraceEvent, event.id)
    assert persisted is not None
    serialized = _serialized(persisted.payload_json)
    assert "+14155552671" not in serialized
    assert "customer@example.com" not in serialized
    assert "123 Main St" not in serialized
    assert "raw-auth" not in serialized
    assert "raw-cookie" not in serialized


def test_unmatched_webhook_event_raw_payload_is_redacted(db_session) -> None:
    WebhookIngestionService(db_session).handle_instagram_payload(
        {
            "object": "instagram",
            "entry": [
                {
                    "id": "unknown-account",
                    "messaging": [
                        {
                            "sender": {"id": "customer-provider-id"},
                            "recipient": {"id": "unknown-account"},
                            "message": {
                                "text": "email customer@example.com phone +14155552671",
                            },
                            "authorization": "Bearer raw-auth",
                            "cookie": "sid=raw-cookie",
                            "access_token": "provider-access-token",
                            "webhook_secret": "provider-webhook-secret",
                        }
                    ],
                }
            ],
        }
    )

    event = db_session.scalar(
        select(WebhookEvent).where(WebhookEvent.provider == WebhookProvider.INSTAGRAM)
    )
    assert event is not None
    serialized = _serialized(event.raw_payload)
    assert "customer@example.com" not in serialized
    assert "+14155552671" not in serialized
    assert "raw-auth" not in serialized
    assert "raw-cookie" not in serialized
    assert "provider-access-token" not in serialized
    assert "provider-webhook-secret" not in serialized
    assert event.raw_payload["entry"][0]["messaging"][0]["access_token"] == REDACTED
