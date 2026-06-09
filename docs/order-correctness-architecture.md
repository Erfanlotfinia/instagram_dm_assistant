# Order Correctness Architecture

## State machine

Orders follow a deterministic lifecycle:

`DRAFT` → `WAITING_FOR_CLARIFICATION` / `READY_FOR_CONFIRMATION` → `RESERVED` → `PAYMENT_PENDING` → `PAID` → `ORDER_CREATED`

Terminal/error paths: `FAILED`, `CANCELLED`, `EXPIRED`.

All transitions are recorded in `order_state_transitions`. Action attempts (allowed/denied) are stored in `action_attempts`.

## Inventory reservations

`InventoryReservationService` manages TTL reservations with Postgres rows, inventory movement ledger entries, and Redis hot cache (`reservation:{id}`).

## Action policy

`ActionPolicyService` gates state-changing actions:

- Tenant (shop) must be active
- Pilot emergency stop must be off
- `pilot_modes` row must permit the action
- Confidence threshold must be satisfied when configured
- Customer confirmation required for payment link and complete

## Webhook idempotency

Meta/Instagram webhooks use Redis `webhook:idem:{key}` plus `UNIQUE(provider, idempotency_key)` on `webhook_events`. Duplicates return HTTP 200 with `dedupe_outcome=duplicate`.

## Compensation

- Payment failed → release reservations, transition to `FAILED`
- Order creation failed after `PAID` → `order_compensation` + `operator_alerts` queues
- Scheduler publishes expired reservation IDs to `reservation_expiry`

## APIs

Flat canonical routes under `/api/v1/orders/*`. Shop-scoped routes in `/api/v1/shops/{shop_id}/orders/*` delegate to the same services.
