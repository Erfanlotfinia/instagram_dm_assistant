# Modira SOC-OS Production Infrastructure

## 1. Text infrastructure diagram

```
Channels -> API/Webhook Ingress -> Kafka replicated topics -> stateless worker groups
                                   |                         |-> scenario-router workers
                                   |                         |-> automation workers
                                   |                         |-> LLM workers
                                   |                         |-> order/payment/inventory workers
                                   |                         `-> handoff workers
                                   |
                                   `-> Postgres event_store/outbox (primary writes)
Workers -> Redis locks/rate limits -> Postgres primary -> read replicas -> analytics
Workers -> OpenTelemetry -> Prometheus -> Grafana + Alertmanager
LLM workers -> tenant queues -> prompt/schema gateway -> provider circuit breaker -> fallback rules
```

## 2. Deployment architecture

Kubernetes runs Dockerized API and worker deployments with rolling updates, readiness/liveness probes, strict resource requests/limits, HPA by CPU and Kafka lag, and separate secrets/config maps. Kafka should run as a managed three-AZ cluster or Strimzi cluster with replication factor 3, `min.insync.replicas=2`, idempotent producers, and `acks=all`. Postgres should be a managed HA primary plus read replicas.

## 3. Event flow and Kafka topology

The durable backbone is Kafka. All events use key `tenant_id:conversation_id` so a single conversation stays ordered while tenants spread across 96 partitions. Topics are defined in `app.services.production_infra`: `soc.message.received.v1`, `soc.scenario.routed.v1`, `soc.commerce.commands.v1`, and `soc.handoff.v1`, each with retry topics at 30s/5m/30m and a DLQ. Consumer groups are per service: scenario router, automation, LLM, order, payment, inventory, and handoff.

Workers commit offsets only after database transactions and idempotency records commit. Retries are at-least-once; exactly-once effects are simulated with `(event_id, consumer_group)` idempotency keys and optimistic version checks.

## 4. Database scaling strategy

Postgres writes go to one primary. Read replicas serve analytics and dashboards. High-volume tables (`event_store`, messages, audit logs, decision traces) are partitioned by `tenant_id` hash and time where appropriate. Strict-consistency domains are orders, payments, and inventory; they use serializable or repeatable-read transactions, unit-of-work boundaries, version columns, idempotency keys, and retry-safe writes. Analytics, logs, recommendations, and traces are eventually consistent.

## 5. Failure recovery scenarios

* Worker crash: Kafka does not commit the offset; another replica reprocesses and idempotency prevents duplicate side effects.
* DB downtime: circuit breakers pause consumers, lag grows durably in Kafka, and API enters read-only or queue-only mode.
* Queue lag: HPA scales workers; LLM is degraded first; rule automation continues; events are never silently dropped.
* LLM outage: tenant LLM queues trip provider circuit breakers and route to automation-only or human handoff.
* Poison messages: retries exhaust into DLQ with correlation ID, tenant, topic, partition, offset, and error metadata for replay tooling.
* Regional partial failure: Kafka replication and Postgres HA preserve committed data; replay uses the immutable event store.

## 6. Observability stack

OpenTelemetry propagates `correlation_id`, `tenant_id`, `conversation_id`, Kafka topic/partition/offset, and worker type across API, Kafka producers, consumers, DB calls, Redis locks, and LLM gateways. Prometheus scrapes API/worker metrics and Kafka lag exporters. Grafana dashboard definitions live under `infra/grafana/dashboards` and cover event throughput, per-tenant load, automation success, LLM fallback, queue lag, worker failures, and API p95/p99 latency. Logs are structured JSON.

## 7. Bottleneck analysis

Likely bottlenecks are LLM provider latency/cost, hot tenants with a small number of high-volume conversations, Postgres write amplification from event and audit records, and inventory/payment transaction contention. Mitigations are tenant quotas, conversation-keyed partitioning, optional tenant shard routing, async analytics replicas, connection pooling, and LLM degradation before core commerce degradation.

## 8. Remaining risks

Production still requires managed Kafka/Postgres provisioning, chaos testing against real infrastructure, capacity tests at 10M+ messages/day, DLQ runbook drills, secrets rotation automation, tenant shard migration tooling, and provider-specific LLM safety evaluations.
