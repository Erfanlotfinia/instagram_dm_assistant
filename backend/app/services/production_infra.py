from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from app.services.soc_events import DomainEventType


class WorkerType(StrEnum):
    SCENARIO_ROUTER = "scenario-router"
    AUTOMATION = "automation"
    LLM = "llm"
    ORDER = "order"
    PAYMENT = "payment"
    INVENTORY = "inventory"
    HANDOFF = "handoff"


class ConsistencyModel(StrEnum):
    STRICT = "strict"
    EVENTUAL = "eventual"


@dataclass(frozen=True, slots=True)
class KafkaTopicSpec:
    name: str
    event_types: tuple[DomainEventType, ...]
    consumer_groups: tuple[str, ...]
    partitions: int = 96
    replication_factor: int = 3
    retention_ms: int = 604_800_000
    retry_topics: tuple[str, ...] = ()
    dlq_topic: str = ""

    def validate(self) -> None:
        if self.partitions < 12:
            raise ValueError("production topics require enough partitions for tenant fanout")
        if self.replication_factor < 3:
            raise ValueError("production topics must be replicated across three brokers")
        if not self.consumer_groups:
            raise ValueError("each topic requires at least one consumer group")
        if not self.dlq_topic:
            raise ValueError("each topic requires a DLQ")


@dataclass(frozen=True, slots=True)
class WorkerSpec:
    worker_type: WorkerType
    consumes: tuple[str, ...]
    consumer_group: str
    min_replicas: int
    max_replicas: int
    idempotency_scope: str = "event_id+consumer_group"
    lock_scope: str = "tenant_id:conversation_id"
    graceful_shutdown_seconds: int = 45

    def validate(self) -> None:
        if self.min_replicas < 2 or self.max_replicas < self.min_replicas:
            raise ValueError("workers must be horizontally scalable and HA")
        if not self.consumes:
            raise ValueError("worker must consume durable topics")


@dataclass(frozen=True, slots=True)
class RateLimitPolicy:
    tenant_messages_per_minute: int = 10_000
    channel_messages_per_minute: int = 2_000
    llm_requests_per_minute: int = 500
    queue_depth_degrade_threshold: int = 50_000
    queue_depth_circuit_open_threshold: int = 250_000


STRICT_TABLES: Final[tuple[str, ...]] = ("orders", "payments", "inventory", "inventory_reservations")
EVENTUAL_TABLES: Final[tuple[str, ...]] = ("analytics", "audit_logs", "recommendations", "decision_traces")


KAFKA_TOPICS: Final[tuple[KafkaTopicSpec, ...]] = (
    KafkaTopicSpec(
        name="soc.message.received.v1",
        event_types=(DomainEventType.MESSAGE_RECEIVED,),
        consumer_groups=("scenario-router-workers",),
        retry_topics=("soc.message.received.retry.30s", "soc.message.received.retry.5m", "soc.message.received.retry.30m"),
        dlq_topic="soc.message.received.dlq",
    ),
    KafkaTopicSpec(
        name="soc.scenario.routed.v1",
        event_types=(DomainEventType.SCENARIO_ROUTED,),
        consumer_groups=("automation-workers", "llm-workers", "handoff-workers"),
        retry_topics=("soc.scenario.routed.retry.30s", "soc.scenario.routed.retry.5m", "soc.scenario.routed.retry.30m"),
        dlq_topic="soc.scenario.routed.dlq",
    ),
    KafkaTopicSpec(
        name="soc.commerce.commands.v1",
        event_types=(DomainEventType.ORDER_CREATED, DomainEventType.PAYMENT_UPDATED, DomainEventType.INVENTORY_UPDATED),
        consumer_groups=("order-workers", "payment-workers", "inventory-workers"),
        retry_topics=("soc.commerce.commands.retry.30s", "soc.commerce.commands.retry.5m", "soc.commerce.commands.retry.30m"),
        dlq_topic="soc.commerce.commands.dlq",
    ),
    KafkaTopicSpec(
        name="soc.handoff.v1",
        event_types=(DomainEventType.HANDOFF_TRIGGERED,),
        consumer_groups=("handoff-workers",),
        retry_topics=("soc.handoff.retry.30s", "soc.handoff.retry.5m", "soc.handoff.retry.30m"),
        dlq_topic="soc.handoff.dlq",
    ),
)


WORKERS: Final[tuple[WorkerSpec, ...]] = (
    WorkerSpec(WorkerType.SCENARIO_ROUTER, ("soc.message.received.v1",), "scenario-router-workers", 4, 80),
    WorkerSpec(WorkerType.AUTOMATION, ("soc.scenario.routed.v1",), "automation-workers", 6, 160),
    WorkerSpec(WorkerType.LLM, ("soc.scenario.routed.v1",), "llm-workers", 4, 120),
    WorkerSpec(WorkerType.ORDER, ("soc.commerce.commands.v1",), "order-workers", 3, 60),
    WorkerSpec(WorkerType.PAYMENT, ("soc.commerce.commands.v1",), "payment-workers", 3, 60),
    WorkerSpec(WorkerType.INVENTORY, ("soc.commerce.commands.v1",), "inventory-workers", 3, 60),
    WorkerSpec(WorkerType.HANDOFF, ("soc.handoff.v1", "soc.scenario.routed.v1"), "handoff-workers", 3, 40),
)


def partition_for(tenant_id: str, conversation_id: str, partitions: int = 96) -> int:
    """Stable Kafka keying: tenant_id + conversation_id preserves conversation order."""
    key = f"{tenant_id}:{conversation_id}".encode("utf-8")
    return int(hashlib.sha256(key).hexdigest()[:8], 16) % partitions


def validate_production_infra_contract() -> None:
    for topic in KAFKA_TOPICS:
        topic.validate()
    for worker in WORKERS:
        worker.validate()
    worker_groups = {worker.consumer_group for worker in WORKERS}
    for topic in KAFKA_TOPICS:
        missing = set(topic.consumer_groups) - worker_groups
        if missing:
            raise ValueError(f"topic {topic.name} has no worker specs for {sorted(missing)}")
