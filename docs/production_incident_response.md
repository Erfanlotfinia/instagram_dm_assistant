# Production Incident Response

## Emergency stop

1. Disable auto-send in shop agent settings.
2. Pause worker/scheduler containers if message processing must stop immediately.
3. Revoke compromised Instagram tokens and rotate secrets if suspected leak.

## Failed webhook spike

1. Check `/api/v1/ready` and RabbitMQ queue depth.
2. Inspect failed jobs UI (`/failed-jobs`) for redacted payloads and error messages.
3. Retry safe jobs after root cause is fixed; ignore poison messages with audit note.

## Payment callback issue

1. Verify order status and inventory reservations in admin orders view.
2. Check payment callback logs; duplicate callbacks must be idempotent.
3. Do not manually mark paid without active reservation unless using authorized admin flow.

## Inventory mismatch

1. Compare `inventory_movements` ledger with variant stock/reserved quantities.
2. Release expired reservations via scheduler/worker cycle.
3. Escalate if SALE movements duplicate for same order.

## Rollback plan

1. Stop workers.
2. Roll back application image to last known good release.
3. Run `alembic downgrade` only when migration is reversible and approved.
4. Restore database from snapshot if data corruption occurred.
