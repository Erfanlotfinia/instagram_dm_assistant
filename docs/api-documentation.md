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
| `/api/v1/shops/{id}/orders` | Orders lifecycle (shop-scoped aliases) |
| `/api/v1/orders/*` | Order correctness canonical routes (draft, clarify, confirm, reserve, payment-link, complete, cancel, timeline) |
| `/api/v1/webhooks/instagram` | Meta inbound webhook |
| `/api/v1/webhooks/meta` | Meta webhook alias with idempotent ingestion |
| `/api/v1/payments/mock/*` | Dev payment simulation |
| `/api/v1/catalog/*` | Catalog import, reindex, normalized products, alias editing |
| `/api/v1/resolve/*` | Product/variant resolver, traces, operator feedback |

## Catalog intelligence

| Method | Path | Body / query |
|--------|------|--------------|
| POST | `/api/v1/catalog/import` | `{ shop_id, rows[] }` |
| POST | `/api/v1/catalog/reindex` | `{ shop_id, product_ids?, batch_size? }` |
| GET | `/api/v1/catalog/products?shop_id=` | pagination + search |
| PATCH | `/api/v1/catalog/products/{id}/aliases?shop_id=` | `{ add[], remove[] }` |
| POST | `/api/v1/resolve/product` | message text + media refs + context |
| POST | `/api/v1/resolve/variant` | message text + product candidates + slots |
| GET | `/api/v1/resolve/{trace_id}?shop_id=` | resolver trace |
| POST | `/api/v1/resolve/{trace_id}/feedback` | operator correction |

See [catalog-intelligence-architecture.md](./catalog-intelligence-architecture.md) for indexing and resolver design.

## Rate limits (when enabled)

| Endpoint | Limit |
|----------|-------|
| `POST /auth/login` | 10/min per IP |
| `POST /webhooks/instagram` | 120/min per IP |
| `POST /conversations/.../messages` | 30/min per IP |

Response `429` includes `Retry-After` header.

## Correlation ID

Every response includes `X-Request-ID`. Pass the same header on retries for log correlation.
