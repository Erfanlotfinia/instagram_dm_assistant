# Troubleshooting Guide

## Webhook not receiving messages

1. Confirm Meta webhook subscription is active.
2. Verify callback URL is reachable (TLS required in production).
3. Check `WEBHOOK_INTERNAL_SECRET` matches Meta dashboard.
4. If `META_APP_SECRET` is set, ensure Meta sends valid `X-Hub-Signature-256`.
5. Confirm `instagram_accounts.ig_user_id` matches webhook `recipient.id`.

## Messages queued but not processed

1. Check worker logs: `docker compose logs -f worker`
2. Verify Redis is healthy: `/api/v1/ready`
3. Look for conversation lock contention (requeue loops).
4. Inspect DLQ: `channel.message.received.dlq`

## Agent not resolving product

1. Verify Instagram post URL mapping exists and is active.
2. Check semantic search / Qdrant health.
3. Review agent run output in conversation detail.

## Order stuck in waiting_for_payment

1. Check `expires_at`; scheduler expires stale orders.
2. Confirm payment callback or manual mark-paid.
3. Verify inventory reservation was not released by cancellation.

## Rate limit errors (429)

- Login, webhook, and outbound message endpoints are rate limited per IP.
- Increase limits via env vars or disable with `RATE_LIMIT_ENABLED=false` (not recommended in production).

## Database migration issues

```bash
docker compose exec backend alembic current
docker compose exec backend alembic upgrade head
```

## Useful log queries

Structured JSON logs include `request_id` for correlation:

```bash
docker compose logs backend | jq 'select(.request_id=="...")'
```
