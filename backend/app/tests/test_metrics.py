from __future__ import annotations

import json

from app.core.metric_labels import (
    HandoffMetricReason,
    ProcessedMessageStatus,
    WebhookMetricResult,
    WorkerDlqReason,
    WorkerRetryReason,
)
from app.core.metrics import (
    AUTOMATION_SUCCESS,
    CHANNEL_INBOUND_MESSAGES,
    CHANNEL_PROCESSED_MESSAGES,
    HANDOFFS,
    metrics_response,
    record_agent_failure,
    record_handoff,
    record_inbound_message,
    record_processed_message,
    record_webhook_event,
)
from app.core.security import encrypt_secret
from app.domain.enums import ChannelProvider
from app.domain.models import ChannelAccount
from app.tests.fixtures.instagram_webhook import SAMPLE_INSTAGRAM_MESSAGE_PAYLOAD


def _metrics_text() -> str:
    body, _ = metrics_response()
    return body.decode()


def _sample_value(body: str, name: str, **labels: str) -> float:
    for line in body.splitlines():
        if not line.startswith(name):
            continue
        if labels and not all(f'{key}="{value}"' in line for key, value in labels.items()):
            continue
        return float(line.rsplit(" ", 1)[1])
    return 0.0


def test_http_metric_path_uses_route_template_not_raw_uuid(
    client, auth_headers, demo_shop
) -> None:
    before = _metrics_text()
    before_count = _sample_value(
        before,
        "http_request_duration_seconds_count",
        method="GET",
        path="/api/v1/shops/{shop_id}/dashboard/metrics",
    )

    response = client.get(
        f"/api/v1/shops/{demo_shop.id}/dashboard/metrics",
        headers=auth_headers,
    )
    assert response.status_code == 200

    after = _metrics_text()
    after_count = _sample_value(
        after,
        "http_request_duration_seconds_count",
        method="GET",
        path="/api/v1/shops/{shop_id}/dashboard/metrics",
    )
    assert after_count > before_count
    assert f'path="{demo_shop.id}"' not in after


def test_webhook_metrics_use_multi_channel_names(client, db_session, demo_shop) -> None:
    account = ChannelAccount(
        shop_id=demo_shop.id,
        provider=ChannelProvider.INSTAGRAM,
        display_name="metrics test",
        external_account_id="17841400000000001",
        webhook_secret_encrypted=encrypt_secret("webhook-secret"),
        webhook_verify_token="verify-token",
    )
    db_session.add(account)
    db_session.commit()

    before = _metrics_text()
    body = json.dumps(SAMPLE_INSTAGRAM_MESSAGE_PAYLOAD, separators=(",", ":")).encode()
    response = client.post(
        "/api/v1/channels/instagram/webhook",
        content=body,
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 200

    after = _metrics_text()
    assert (
        _sample_value(
            after,
            "modira_webhook_events_total",
            provider="instagram",
            result="processed",
        )
        >= 1
    )
    assert _sample_value(after, "modira_channel_inbound_messages_total", provider="instagram") >= 1
    assert _sample_value(
        after,
        "modira_webhook_events_total",
        provider="instagram",
        result="processed",
    ) > _sample_value(
        before,
        "modira_webhook_events_total",
        provider="instagram",
        result="processed",
    )


def test_metric_helpers_use_controlled_provider_and_reason_labels() -> None:
    before = _metrics_text()

    record_inbound_message("not-a-real-provider")
    record_agent_failure(None)
    record_handoff("instagram", HandoffMetricReason.POLICY)
    record_webhook_event(ChannelProvider.INSTAGRAM, WebhookMetricResult.DUPLICATE)

    after = _metrics_text()
    assert _sample_value(after, "modira_channel_inbound_messages_total", provider="unknown") >= 1
    assert _sample_value(after, "modira_agent_failed_runs_total", provider="unknown") >= 1
    assert _sample_value(after, "modira_handoffs_total", provider="instagram", reason="policy") >= 1
    assert (
        _sample_value(
            after,
            "modira_webhook_events_total",
            provider="instagram",
            result="duplicate",
        )
        >= 1
    )

    allowed_providers = {"instagram", "whatsapp", "telegram", "bale", "rubika", "unknown"}
    allowed_handoff_reasons = {reason.value for reason in HandoffMetricReason}
    allowed_webhook_results = {result.value for result in WebhookMetricResult}
    allowed_retry_reasons = {reason.value for reason in WorkerRetryReason}
    allowed_dlq_reasons = {reason.value for reason in WorkerDlqReason}

    for line in after.splitlines():
        if line.startswith("modira_channel_inbound_messages_total"):
            assert 'provider="' in line
            provider = line.split('provider="', 1)[1].split('"', 1)[0]
            assert provider in allowed_providers
        if line.startswith("modira_handoffs_total"):
            reason = line.split('reason="', 1)[1].split('"', 1)[0]
            assert reason in allowed_handoff_reasons
        if line.startswith("modira_webhook_events_total"):
            result = line.split('result="', 1)[1].split('"', 1)[0]
            assert result in allowed_webhook_results
        if line.startswith("modira_queue_retries_total"):
            reason = line.split('reason="', 1)[1].split('"', 1)[0]
            assert reason in allowed_retry_reasons
        if line.startswith("modira_queue_dlq_total"):
            reason = line.split('reason="', 1)[1].split('"', 1)[0]
            assert reason in allowed_dlq_reasons

    assert _sample_value(after, "instagram_inbound_messages_total") >= _sample_value(
        before, "instagram_inbound_messages_total"
    )


def test_processed_message_status_records_success() -> None:
    before = _metrics_text()
    record_processed_message("instagram", ProcessedMessageStatus.SUCCESS)
    after = _metrics_text()
    assert (
        _sample_value(
            after,
            "modira_channel_processed_messages_total",
            provider="instagram",
            status="success",
        )
        > _sample_value(
            before,
            "modira_channel_processed_messages_total",
            provider="instagram",
            status="success",
        )
    )


def test_processed_message_status_records_failure() -> None:
    before = _metrics_text()
    record_processed_message("instagram", "failure")
    after = _metrics_text()
    assert (
        _sample_value(
            after,
            "modira_channel_processed_messages_total",
            provider="instagram",
            status="failure",
        )
        >= 1
    )
    assert (
        _sample_value(
            after,
            "modira_channel_processed_messages_total",
            provider="instagram",
            status="success",
        )
        == _sample_value(
            before,
            "modira_channel_processed_messages_total",
            provider="instagram",
            status="success",
        )
    )


def test_processed_message_unknown_status_maps_to_unknown() -> None:
    before = _metrics_text()
    record_processed_message("instagram", "garbage")
    after = _metrics_text()
    assert (
        _sample_value(
            after,
            "modira_channel_processed_messages_total",
            provider="instagram",
            status="unknown",
        )
        >= 1
    )


def test_no_tenant_id_label_in_prometheus_metric_definitions() -> None:
    metric_objects = [
        CHANNEL_INBOUND_MESSAGES,
        CHANNEL_PROCESSED_MESSAGES,
        HANDOFFS,
        AUTOMATION_SUCCESS,
    ]
    for metric in metric_objects:
        assert "tenant_id" not in metric._labelnames

    body = _metrics_text()
    assert 'tenant_id="' not in body
    assert "shop_id=" not in body
    assert "customer_id=" not in body
    assert "conversation_id=" not in body
