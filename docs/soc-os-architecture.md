# Modira SOC-OS Distributed Architecture

```text
Meta/Channel Webhooks
  -> Signature + Tenant Resolver
  -> DomainEvent(message_received)
  -> Immutable Event Store (append only, tenant/conversation indexes)
  -> EventBus / Kafka-style Backbone (partition key: tenant_id:conversation_id)
      -> scenario-router consumer group -> scenario_routed
      -> automation-workers group -> automation_executed / handoff_triggered
      -> llm-workers group -> llm_fallback_called (tenant memory sandbox)
      -> order-workers group -> order_created (OCC + lock)
      -> payment-workers group -> payment_updated (strict state machine)
      -> inventory-workers group -> inventory_updated (strict reservation lock)
      -> DLQ + retry topics
  -> OpenTelemetry traces + Prometheus metrics + JSON logs
```

## Event flow map

1. Webhook ingress validates a per-tenant signature and emits `message_received`.
2. Scenario routing consumes the ordered conversation stream and emits `scenario_routed`.
3. ExecutionPolicyGate authorizes automation, handoff, or LLM fallback before a handler runs.
4. Side-effect workers publish `automation_executed`, `order_created`, `payment_updated`, `inventory_updated`, `llm_fallback_called`, or `handoff_triggered`.
5. Failed consumers retry with exponential backoff and then write the original immutable event to DLQ.

## Multi-tenant isolation model

Every event and request carries `tenant_id` and `shop_id`. Partitions, replay queries, LLM memory keys, worker poll scopes, and service calls are scoped to that tuple. Consumers reject events whose tenant scope does not match their execution context.

## Event store design

The event store is append-only. Updates and deletes are explicit policy violations. It indexes by tenant, conversation, and event time, supports full tenant replay, partial conversation replay, time-travel cutoffs, and audit compliance mode.

## Worker system design

Workers are independent consumer groups: automation, order, payment, inventory, LLM, and handoff. Consumer offsets are independent per group. Processing is idempotent by `event_id`; retries use exponential backoff; exhausted messages move to DLQ.

## Observability stack

The stack uses JSON logs with correlation fields, OpenTelemetry-compatible trace/correlation IDs, and Prometheus metrics for event latency, scenario routing time, LLM latency, automation success, and channel failure rates.

## Consistency and failure model

Order, payment, and inventory handlers must use distributed locks plus optimistic concurrency/version checks. Analytics may be eventually consistent. Duplicate events, delayed messages, out-of-order cross-partition delivery, partial failures, and worker crashes are handled by partition ordering, idempotency, retries, DLQ, and replay-safe reconstruction.

## Replay safety

Replay runs in dry-run/sandbox mode. It rehydrates deterministic state and refuses order creation, payment mutation, and inventory mutation.

## Remaining risks

A real Kafka deployment still requires production broker provisioning, topic ACLs, schema registry enforcement, and database migrations for physical partitioned event tables in non-test environments.
