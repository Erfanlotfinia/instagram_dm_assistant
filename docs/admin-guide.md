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
- Keep `INSTAGRAM_APP_SECRET` confidential.
- Review audit logs for login and admin actions.
- Limit production CORS origins to the admin domain.

## Monitoring

- `/api/v1/ready` — dependency health
- `/api/v1/metrics` — Prometheus counters (messages, orders, handoffs, queue lag)
- RabbitMQ DLQ `instagram.message.received.dlq` — failed jobs
