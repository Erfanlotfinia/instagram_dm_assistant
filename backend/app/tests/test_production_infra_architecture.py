from app.services.production_infra import (
    EVENTUAL_TABLES,
    KAFKA_TOPICS,
    STRICT_TABLES,
    WORKERS,
    RateLimitPolicy,
    WorkerType,
    partition_for,
    validate_production_infra_contract,
)
from app.services.soc_events import DomainEventType


def test_production_kafka_topology_has_retries_dlq_and_consumer_groups():
    validate_production_infra_contract()
    topics = {topic.name: topic for topic in KAFKA_TOPICS}

    assert "soc.message.received.v1" in topics
    assert topics["soc.message.received.v1"].event_types == (DomainEventType.MESSAGE_RECEIVED,)
    assert topics["soc.message.received.v1"].retry_topics == (
        "soc.message.received.retry.30s",
        "soc.message.received.retry.5m",
        "soc.message.received.retry.30m",
    )
    assert topics["soc.message.received.v1"].dlq_topic == "soc.message.received.dlq"
    assert all(topic.replication_factor >= 3 for topic in KAFKA_TOPICS)


def test_partitioning_uses_tenant_and_conversation_for_ordering():
    first = partition_for("tenant-a", "conversation-1")
    second = partition_for("tenant-a", "conversation-1")
    different_conversation = partition_for("tenant-a", "conversation-2")
    different_tenant = partition_for("tenant-b", "conversation-1")

    assert first == second
    assert different_conversation != first or different_tenant != first


def test_all_required_worker_types_are_stateless_and_ha():
    worker_types = {worker.worker_type for worker in WORKERS}

    assert worker_types == set(WorkerType)
    assert all(worker.min_replicas >= 2 for worker in WORKERS)
    assert all(worker.idempotency_scope == "event_id+consumer_group" for worker in WORKERS)
    assert all(worker.lock_scope == "tenant_id:conversation_id" for worker in WORKERS)


def test_database_consistency_boundaries_are_explicit():
    assert {"orders", "payments", "inventory"}.issubset(STRICT_TABLES)
    assert {"analytics", "audit_logs", "recommendations"}.issubset(EVENTUAL_TABLES)


def test_backpressure_policy_degrades_llm_before_queue_overload():
    policy = RateLimitPolicy()

    assert policy.llm_requests_per_minute < policy.tenant_messages_per_minute
    assert policy.queue_depth_degrade_threshold < policy.queue_depth_circuit_open_threshold
