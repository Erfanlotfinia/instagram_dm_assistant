from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

from app.core.metric_labels import (
    HandoffMetricReason,
    ProcessedMessageStatus,
    WebhookIgnoredReason,
    WebhookMetricResult,
    WorkerDlqReason,
    WorkerRetryReason,
    normalize_handoff_reason,
    normalize_processed_message_status,
    normalize_provider,
)

CHANNEL_INBOUND_MESSAGES = Counter(
    "modira_channel_inbound_messages_total",
    "Total inbound channel messages persisted and queued for processing",
    ["provider"],
)
CHANNEL_PROCESSED_MESSAGES = Counter(
    "modira_channel_processed_messages_total",
    "Total inbound messages successfully processed by the agent worker",
    ["provider", "status"],
)
AGENT_FAILED_RUNS = Counter(
    "modira_agent_failed_runs_total",
    "Total agent runs that ended in failure",
    ["provider"],
)
HANDOFFS = Counter(
    "modira_handoffs_total",
    "Total conversations escalated to human handoff",
    ["provider", "reason"],
)
ORDERS_CREATED = Counter(
    "modira_orders_created_total",
    "Total orders created (draft or confirmed)",
    ["provider"],
)
ORDERS_PAID = Counter(
    "modira_orders_paid_total",
    "Total orders marked as paid",
)
QUEUE_LAG = Gauge(
    "modira_queue_lag_messages",
    "Approximate number of messages waiting in a queue",
    ["queue_name"],
)
QUEUE_RETRIES = Counter(
    "modira_queue_retries_total",
    "Total inbound messages scheduled for delayed retry by the worker",
    ["queue_name", "reason"],
)
QUEUE_DLQ = Counter(
    "modira_queue_dlq_total",
    "Total inbound messages published to the dead-letter queue by the worker",
    ["queue_name", "reason"],
)
WEBHOOK_EVENTS = Counter(
    "modira_webhook_events_total",
    "Total webhook ingestion outcomes by provider and result",
    ["provider", "result"],
)
WEBHOOK_EVENTS_IGNORED = Counter(
    "modira_webhook_ignored_total",
    "Total ignored webhook deliveries with a controlled reason",
    ["provider", "reason"],
)

# deprecated: remove next release
_LEGACY_INBOUND_MESSAGES = Counter(
    "instagram_inbound_messages_total",
    "Deprecated alias for modira_channel_inbound_messages_total",
)
_LEGACY_PROCESSED_MESSAGES = Counter(
    "instagram_processed_messages_total",
    "Deprecated alias for modira_channel_processed_messages_total",
)
_LEGACY_FAILED_AGENT_RUNS = Counter(
    "instagram_failed_agent_runs_total",
    "Deprecated alias for modira_agent_failed_runs_total",
)
_LEGACY_HANDOFF_COUNT = Counter(
    "instagram_handoff_total",
    "Deprecated alias for modira_handoffs_total",
)
_LEGACY_CREATED_ORDERS = Counter(
    "instagram_created_orders_total",
    "Deprecated alias for modira_orders_created_total",
)
_LEGACY_PAID_ORDERS = Counter(
    "instagram_paid_orders_total",
    "Deprecated alias for modira_orders_paid_total",
)
_LEGACY_QUEUE_LAG = Gauge(
    "instagram_queue_lag_messages",
    "Deprecated alias for modira_queue_lag_messages",
)
_LEGACY_RETRIED_MESSAGES = Counter(
    "instagram_retried_messages_total",
    "Deprecated alias for modira_queue_retries_total",
)
_LEGACY_DLQ_MESSAGES = Counter(
    "instagram_dlq_messages_total",
    "Deprecated alias for modira_queue_dlq_total",
)

HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

EVENT_LATENCY = Histogram(
    "soc_event_latency_seconds",
    "End-to-end domain event latency by event type and consumer group",
    ["event_type", "consumer_group"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
SCENARIO_ROUTING_TIME = Histogram(
    "soc_scenario_routing_seconds",
    "Scenario routing decision duration",
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5),
)
LLM_LATENCY = Histogram(
    "soc_llm_latency_seconds",
    "LLM fallback latency by tenant-safe model label",
    ["model"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
)
AUTOMATION_SUCCESS = Counter(
    "soc_automation_success_total",
    "Successful automation executions",
    ["automation"],
)
CHANNEL_FAILURES = Counter(
    "soc_channel_failures_total",
    "Failures by inbound/outbound channel",
    ["channel", "failure_type"],
)

# Backward-compatible constant aliases used by existing imports.
INBOUND_MESSAGES = _LEGACY_INBOUND_MESSAGES
PROCESSED_MESSAGES = _LEGACY_PROCESSED_MESSAGES
FAILED_AGENT_RUNS = _LEGACY_FAILED_AGENT_RUNS
HANDOFF_COUNT = _LEGACY_HANDOFF_COUNT
CREATED_ORDERS = _LEGACY_CREATED_ORDERS
PAID_ORDERS = _LEGACY_PAID_ORDERS
RETRIED_MESSAGES = _LEGACY_RETRIED_MESSAGES
DLQ_MESSAGES = _LEGACY_DLQ_MESSAGES


def record_inbound_message(provider: str | object | None) -> None:
    provider_label = normalize_provider(provider)
    CHANNEL_INBOUND_MESSAGES.labels(provider=provider_label).inc()
    _LEGACY_INBOUND_MESSAGES.inc()


def record_processed_message(
    provider: str | object | None,
    status: ProcessedMessageStatus | str = ProcessedMessageStatus.SUCCESS,
) -> None:
    provider_label = normalize_provider(provider)
    status_label = normalize_processed_message_status(status).value
    CHANNEL_PROCESSED_MESSAGES.labels(provider=provider_label, status=status_label).inc()
    _LEGACY_PROCESSED_MESSAGES.inc()


def record_agent_failure(provider: str | object | None) -> None:
    provider_label = normalize_provider(provider)
    AGENT_FAILED_RUNS.labels(provider=provider_label).inc()
    _LEGACY_FAILED_AGENT_RUNS.inc()


def record_handoff(
    provider: str | object | None,
    reason: HandoffMetricReason | str | None = None,
) -> None:
    provider_label = normalize_provider(provider)
    reason_label = normalize_handoff_reason(reason).value
    HANDOFFS.labels(provider=provider_label, reason=reason_label).inc()
    _LEGACY_HANDOFF_COUNT.inc()


def record_order_created(provider: str | object | None) -> None:
    provider_label = normalize_provider(provider)
    ORDERS_CREATED.labels(provider=provider_label).inc()
    _LEGACY_CREATED_ORDERS.inc()


def record_order_paid() -> None:
    ORDERS_PAID.inc()
    _LEGACY_PAID_ORDERS.inc()


def record_queue_lag(queue_name: str, depth: int) -> None:
    QUEUE_LAG.labels(queue_name=queue_name).set(depth)
    _LEGACY_QUEUE_LAG.set(depth)


def record_queue_retry(queue_name: str, reason: WorkerRetryReason) -> None:
    QUEUE_RETRIES.labels(queue_name=queue_name, reason=reason.value).inc()
    _LEGACY_RETRIED_MESSAGES.inc()


def record_queue_dlq(queue_name: str, reason: WorkerDlqReason) -> None:
    QUEUE_DLQ.labels(queue_name=queue_name, reason=reason.value).inc()
    _LEGACY_DLQ_MESSAGES.inc()


def record_webhook_event(
    provider: str | object | None,
    result: WebhookMetricResult,
    ignored_reason: WebhookIgnoredReason | None = None,
) -> None:
    provider_label = normalize_provider(provider)
    WEBHOOK_EVENTS.labels(provider=provider_label, result=result.value).inc()
    if result == WebhookMetricResult.IGNORED and ignored_reason is not None:
        WEBHOOK_EVENTS_IGNORED.labels(
            provider=provider_label,
            reason=ignored_reason.value,
        ).inc()


def metrics_response() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST
