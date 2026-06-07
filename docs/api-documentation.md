# API Documentation

## Interactive docs

When `APP_ENV` is not `production`:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Authentication

```http
POST /api/v1/auth/login
Content-Type: application/json

{"email": "admin@shop.com", "password": "secret123"}
```

Response: `{ "access_token": "..." }`

Use header: `Authorization: Bearer <token>`

## Health & observability

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Liveness |
| `GET /api/v1/ready` | Readiness (postgres, redis, rabbitmq, qdrant) |
| `GET /api/v1/metrics` | Prometheus metrics |

## Core resources

All shop-scoped routes require membership in the shop.

| Prefix | Description |
|--------|-------------|
| `/api/v1/shops` | Shops, settings, dashboard, Instagram accounts |
| `/api/v1/shops/{id}/products` | Product catalog |
| `/api/v1/shops/{id}/conversations` | Conversations, handoff, manual messages |
| `/api/v1/shops/{id}/orders` | Orders lifecycle |
| `/api/v1/webhooks/instagram` | Meta inbound webhook |
| `/api/v1/payments/mock/*` | Dev payment simulation |

## Rate limits (when enabled)

| Endpoint | Limit |
|----------|-------|
| `POST /auth/login` | 10/min per IP |
| `POST /webhooks/instagram` | 120/min per IP |
| `POST /conversations/.../messages` | 30/min per IP |

Response `429` includes `Retry-After` header.

## Correlation ID

Every response includes `X-Request-ID`. Pass the same header on retries for log correlation.
