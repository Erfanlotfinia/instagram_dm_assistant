# Admin Guide

Admins configure shops, catalog, Instagram integration, and agent behavior.

## Shop setup

1. Create shop and invite members with appropriate roles (`owner`, `admin`, `operator`).
2. Set default currency and agent settings under **Settings**.
3. Connect Instagram account with encrypted access token.
4. Map Instagram post URLs to products.

## Agent settings

| Setting | Purpose |
|---------|---------|
| Auto reply | Enable/disable automated responses |
| Intent confidence threshold | Handoff when intent confidence is low |
| Slot confidence threshold | Handoff when extracted slots are uncertain |
| Handoff mode | Policy for human escalation |
| Default language | Persian (`fa`) recommended for Iranian pilots |

## Catalog management

- Create products and variants with accurate stock.
- Use **Instagram mapping** for known post URLs.
- Run semantic resolve test for unmapped posts.

## Security responsibilities

- Rotate `JWT_SECRET_KEY` and `TOKEN_ENCRYPTION_KEY` on compromise.
- Keep `META_APP_SECRET` confidential.
- Review audit logs for login and admin actions.
- Limit production CORS origins to the admin domain.

## Monitoring

- `/api/v1/ready` — dependency health
- `/api/v1/metrics` — Prometheus counters and histograms:
  - `modira_channel_inbound_messages_total`, `modira_channel_processed_messages_total` (by `provider`)
  - `modira_webhook_events_total` (by `provider`, `result`)
  - `modira_queue_lag_messages`, `modira_queue_retries_total`, `modira_queue_dlq_total` (by `queue_name`, `reason`)
  - `modira_handoffs_total`, `modira_orders_created_total`, `modira_orders_paid_total`, `modira_agent_failed_runs_total`
  - `http_request_duration_seconds` uses FastAPI route templates in the `path` label (not raw UUIDs)
  - Legacy `instagram_*` metric names are deprecated aliases and will be removed in the next release
- RabbitMQ DLQ `channel.message.received.dlq` — failed jobs
