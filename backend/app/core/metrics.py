from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

INBOUND_MESSAGES = Counter(
    "instagram_inbound_messages_total",
    "Total inbound Instagram messages received via webhook",
)
PROCESSED_MESSAGES = Counter(
    "instagram_processed_messages_total",
    "Total inbound messages successfully processed by the agent worker",
)
FAILED_AGENT_RUNS = Counter(
    "instagram_failed_agent_runs_total",
    "Total agent runs that ended in failure",
)
HANDOFF_COUNT = Counter(
    "instagram_handoff_total",
    "Total conversations escalated to human handoff",
)
CREATED_ORDERS = Counter(
    "instagram_created_orders_total",
    "Total orders created (draft or confirmed)",
)
PAID_ORDERS = Counter(
    "instagram_paid_orders_total",
    "Total orders marked as paid",
)
QUEUE_LAG = Gauge(
    "instagram_queue_lag_messages",
    "Approximate number of messages waiting in the primary queue",
)
HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)


def metrics_response() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST
