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
    ["tenant_id", "automation"],
)
CHANNEL_FAILURES = Counter(
    "soc_channel_failures_total",
    "Failures by inbound/outbound channel",
    ["channel", "failure_type"],
)
