# API Documentation

Interactive OpenAPI docs are available in non-production environments:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Health & observability

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Liveness probe |
| `GET /api/v1/health` | Liveness probe (versioned) |
| `GET /api/v1/ready` | Readiness: postgres, redis, rabbitmq, qdrant |
| `GET /api/v1/metrics` | Prometheus metrics |

## Authentication

| Endpoint | Description |
|----------|-------------|
| `POST /api/v1/auth/login` | Email/password login (rate limited) |
| `GET /api/v1/auth/me` | Current user profile |

## Webhooks

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/webhooks/instagram` | Meta verification challenge |
| `POST /api/v1/webhooks/instagram` | Inbound messaging (rate limited, signature optional) |

## Shop-scoped resources

All routes under `/api/v1/shops/{shop_id}/...` require JWT and shop membership.

Key groups:

- **Shops** — CRUD, settings, dashboard, Instagram accounts
- **Products** — catalog, variants, Instagram product maps
- **Conversations** — list, detail, take-over, release, manual messages
- **Orders** — list, confirm, cancel, mark-paid, ship
- **Semantic search** — product similarity search

## Payments (dev)

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/payments/mock/pay/{payment_id}` | Mock payment page |
| `POST /api/v1/payments/mock/callback` | Mock payment callback |

## Request tracing

All responses include `X-Request-ID`. Pass `X-Request-ID` on inbound requests to propagate correlation IDs.
