# Modira API Reference — Developer Guide

REST API for the **Modira Enterprise Admin OS**: multi-channel commerce operations, catalog intelligence, order correctness, automation, analytics, and system administration.

**Version:** `1.0.0` (see `backend/app/main.py`)  
**Base URL (local):** `http://localhost:8000`  
**API prefix:** `/api/v1`

---

## Table of contents

1. [Quick start](#quick-start)
2. [Interactive OpenAPI docs](#interactive-openapi-docs)
3. [Conventions](#conventions)
4. [Authentication & authorization](#authentication--authorization)
5. [Health & observability](#health--observability)
6. [Realtime (WebSocket)](#realtime-websocket)
7. [Auth](#auth)
8. [Shops](#shops)
9. [Products & variants](#products--variants)
10. [Catalog intelligence](#catalog-intelligence)
11. [Catalog attributes](#catalog-attributes)
12. [Resolver](#resolver)
13. [Semantic search](#semantic-search)
14. [Conversations & customers](#conversations--customers)
15. [Suggested replies](#suggested-replies)
16. [Orders (shop-scoped)](#orders-shop-scoped)
17. [Order correctness (canonical lifecycle)](#order-correctness-canonical-lifecycle)
18. [Recovery & upsells](#recovery--upsells)
19. [Channels & webhooks](#channels--webhooks)
20. [Instagram connect](#instagram-connect)
21. [Telegram connect](#telegram-connect)
22. [Payments (development)](#payments-development)
23. [Agent settings & risk](#agent-settings--risk)
24. [Pilot & pilot mode](#pilot--pilot-mode)
25. [Policies & triggers](#policies--triggers)
26. [Social admin & automation](#social-admin--automation)
27. [Scenarios & incidents](#scenarios--incidents)
28. [Decision traces](#decision-traces)
29. [Analytics](#analytics)
30. [Simulator & TRL validation](#simulator--trl-validation)
31. [Failed jobs](#failed-jobs)
32. [Related documentation](#related-documentation)

---

## Quick start

```bash
# 1. Start the stack (from repo root)
docker compose up backend

# 2. Log in (Bearer token for scripts / Swagger)
curl -s -X POST "http://localhost:8000/api/v1/auth/login?token_only=true" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@shop.com","password":"secret123"}'

# 3. Call a protected endpoint
curl -s "http://localhost:8000/api/v1/shops" \
  -H "Authorization: Bearer <access_token>"
```

For browser-based admin UI development, prefer the **cookie session** flow (see [Authentication](#authentication--authorization)). The React admin app uses `credentials: 'include'` and CSRF headers on mutating requests.

---

## Interactive OpenAPI docs

When `APP_ENV` is **not** `production`, FastAPI serves machine-readable schemas and interactive explorers:

| UI | URL |
|----|-----|
| Swagger UI | `http://localhost:8000/docs` |
| ReDoc | `http://localhost:8000/redoc` |
| OpenAPI JSON | `http://localhost:8000/openapi.json` |

**Use OpenAPI as the source of truth for request/response field names and types.** This guide describes behavior, auth, and routing; Pydantic schemas live under `backend/app/schemas/`.

Swagger is pre-configured with **BearerAuth** and **CsrfToken** security schemes (`backend/app/core/openapi.py`).

---

## Conventions

### Content type

All JSON endpoints expect and return `Content-Type: application/json` unless noted (webhook verification returns plain text).

### Identifiers

- `shop_id`, `conversation_id`, `order_id`, and other resource IDs are **UUIDs** (RFC 4122 string form in URLs and JSON).
- Path parameters use snake_case names matching the route definitions.

### Shop scoping

Most business routes include `{shop_id}` in the path. The caller must:

1. Be authenticated.
2. Be a **member** of that shop (`ShopMember` record).

Some routes additionally require a minimum **shop role** (`OPERATOR`, `ADMIN`, or `OWNER`). See [Authorization](#authorization).

### Pagination

List endpoints that paginate accept:

| Query param | Default | Constraints |
|-------------|---------|-------------|
| `page` | `1` | ≥ 1 |
| `page_size` | varies (often `25`) | 1–100 |

Paginated responses include total counts in their response models (see OpenAPI).

### Date ranges (analytics)

Analytics endpoints accept either pair:

- `date_from` / `date_to`, or
- `start` / `end`

Both resolve to the same internal range via `resolve_analytics_range`.

### Correlation ID

Every response includes **`X-Request-ID`**. Send the same header on retries to correlate logs across services and workers.

### Error responses

Errors return JSON:

```json
{
  "detail": "Human-readable message or validation error list",
  "status_code": 401
}
```

| Status | Meaning |
|--------|---------|
| `400` | Bad request / invalid payload |
| `401` | Not authenticated (missing or expired JWT) |
| `403` | Authenticated but forbidden (shop access, role, webhook signature) |
| `404` | Resource not found |
| `422` | Validation error (`detail` is a Pydantic error list) |
| `429` | Rate limited (`Retry-After` header set when enabled) |
| `502` | Upstream dependency failure (embeddings, Qdrant) on catalog/resolve routes |
| `503` | Readiness failure (Postgres unavailable) |

### Rate limits (when enabled)

| Endpoint pattern | Limit |
|------------------|-------|
| `POST /api/v1/auth/login` | 10/min per IP |
| `POST /api/v1/channels/*/webhook` | 120/min per IP |
| `POST .../conversations/.../messages` and suggested-reply send | 30/min per IP |

---

## Authentication & authorization

Modira supports two client patterns:

### 1. Bearer JWT (recommended for Swagger, curl, CI)

```http
POST /api/v1/auth/login?token_only=true
Content-Type: application/json

{"email": "admin@shop.com", "password": "secret123"}
```

Response includes `access_token`. Use:

```http
Authorization: Bearer <access_token>
```

`token_only=true` skips HttpOnly cookies so Swagger mutating requests are not blocked by CSRF checks. **Only available when not in production.**

Access tokens expire after the configured JWT TTL (default **15 minutes**). Repeat login when you receive `401`.

### 2. HttpOnly cookie session (browser admin app)

Login **without** `token_only` sets:

| Cookie | Purpose |
|--------|---------|
| `__Host-modira_access` | JWT access token |
| `__Host-modira_refresh` | Refresh token |
| `modira_csrf` | CSRF token (readable by JS) |

Mutating requests (`POST`, `PUT`, `PATCH`, `DELETE`) with cookie auth require:

```http
X-CSRF-Token: <value of modira_csrf cookie>
```

Refresh the session with `POST /api/v1/auth/refresh` (uses refresh cookie). Logout with `POST /api/v1/auth/logout`.

### Authorization

**Global user roles** (`User.role`): used on a few platform routes (e.g. order correctness clarify/confirm requires global `OPERATOR+`).

**Shop member roles** (`ShopMember.role`), ranked low → high:

| Role | Typical use |
|------|-------------|
| `OPERATOR` | Inbox, orders, manual messages, recovery rules |
| `ADMIN` | Channel credentials, pilot settings, failed jobs, semantic search |
| `OWNER` | Highest shop privilege (same rank checks as ADMIN where ADMIN is required) |

In route tables below:

- **Member** = any shop member
- **Operator+** = `OPERATOR`, `ADMIN`, or `OWNER`
- **Admin+** = `ADMIN` or `OWNER`
- **Public** = no auth (webhooks, health, mock payments)

---

## Health & observability

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/health` | Public | Liveness probe (`{"status":"ok"}`) |
| `GET` | `/ready` | Public | Readiness at root (same logic as versioned) |
| `GET` | `/api/v1/health` | Public | Versioned liveness |
| `GET` | `/api/v1/ready` | Public | Readiness: postgres, redis, rabbitmq, qdrant, LLM config |
| `GET` | `/api/v1/metrics` | Public | Prometheus metrics |

**Readiness** returns `503` when Postgres is down. Other dependency failures yield `degraded` status but may still return `200`.

---

## Realtime (WebSocket)

| Protocol | Path | Auth |
|----------|------|------|
| WebSocket | `/api/v1/ws/shops/{shop_id}` | Cookie JWT + shop membership |

Connect from an allowed CORS origin with the `__Host-modira_access` cookie. Events are JSON envelopes:

```json
{"type": "message.created", "payload": {"conversation_id": "..."}, "timestamp": "2026-06-29T12:00:00+00:00"}
```

System events include `realtime.connected`, `realtime.unavailable`, and periodic `ping`. Events are relayed from Redis pub/sub (`app.realtime.publisher`).

---

## Auth

Prefix: `/api/v1/auth`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/login` | Public (rate limited) | Email/password login. Query: `token_only` (bool, non-prod). Body: `{email, password}`. Returns `LoginResponse`. |
| `POST` | `/refresh` | Refresh cookie | Rotate session; returns new tokens in cookies + `LoginResponse`. |
| `POST` | `/logout` | Cookie session | Revoke refresh token; clears cookies. `204`. |
| `GET` | `/me` | Bearer or cookie | Current user profile (`UserRead`). |
| `PATCH` | `/me` | Bearer or cookie | Update profile. Body: `{full_name}`. |
| `POST` | `/change-password` | Bearer or cookie | Body: `{current_password, new_password}`. `204`. |

---

## Shops

Prefix: `/api/v1/shops`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `` | Authenticated | List shops for current user. |
| `POST` | `` | Authenticated | Create shop. Body: `ShopCreate`. |
| `GET` | `/{shop_id}` | Member | Get shop details. |
| `PATCH` | `/{shop_id}` | Admin+ | Update shop. Body: `ShopUpdate`. |
| `GET` | `/{shop_id}/settings` | Member | Shop settings. |
| `PATCH` | `/{shop_id}/agent-settings` | Admin+ | Legacy agent settings on shop record. Body: `ShopAgentSettings`. |
| `GET` | `/{shop_id}/dashboard/metrics` | Member | Dashboard KPI snapshot. |
| `GET` | `/{shop_id}/dashboard/trends` | Member | Trend series. Query: `period` (default `7d`). |
| `GET` | `/{shop_id}/onboarding-status` | Member | Onboarding checklist state. |
| `GET` | `/{shop_id}/members` | Member | Shop membership list. |
| `GET` | `/{shop_id}/instagram-accounts` | Member | Legacy Instagram account links. |
| `POST` | `/{shop_id}/instagram-accounts` | Member | Create Instagram account link. Body: `InstagramAccountCreate`. |

---

## Products & variants

Prefix: `/api/v1/shops`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/{shop_id}/products` | Member | List products. |
| `POST` | `/{shop_id}/products` | Member | Create product. Body: `ProductCreate`. |
| `GET` | `/{shop_id}/products/{product_id}` | Member | Get product. |
| `PATCH` | `/{shop_id}/products/{product_id}` | Member | Update product. Body: `ProductUpdate`. |
| `DELETE` | `/{shop_id}/products/{product_id}` | Member | Delete product. `204`. |
| `GET` | `/{shop_id}/products/{product_id}/variants` | Member | List variants. |
| `POST` | `/{shop_id}/products/{product_id}/variants` | Member | Create variant. Body: `VariantCreate`. |
| `PATCH` | `/{shop_id}/variants/{variant_id}` | Member | Update variant. |
| `DELETE` | `/{shop_id}/variants/{variant_id}` | Member | Archive variant (soft delete). `204`. |
| `POST` | `/{shop_id}/products/{product_id}/variants/{variant_id}/archive` | Member | Archive with reason. Body: `VariantArchiveRequest`. |
| `GET` | `/{shop_id}/instagram-product-maps` | Member | Instagram ↔ catalog mappings. |
| `POST` | `/{shop_id}/instagram-product-maps` | Member | Create mapping. |
| `PATCH` | `/{shop_id}/instagram-product-maps/{map_id}` | Member | Update mapping. |
| `POST` | `/{shop_id}/resolve-instagram-product` | Member | Resolve IG product reference to catalog item. |

---

## Catalog intelligence

Prefix: `/api/v1/catalog`

Bulk import, vector reindex, normalized product listing, and alias editing. See [catalog-intelligence-architecture.md](./catalog-intelligence-architecture.md).

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/import` | Member (via `shop_id` in body) | Import catalog rows. Body: `{shop_id, rows[]}`. Returns job. |
| `POST` | `/reindex` | Member (via body) | Re-embed products. Body: `{shop_id, product_ids?, batch_size?}`. |
| `GET` | `/products` | Member | Paginated normalized products. Query: `shop_id`, `page`, `page_size`, `search`. |
| `PATCH` | `/products/{product_id}/aliases` | Member | Patch aliases. Query: `shop_id`. Body: `{add[], remove[]}`. |

Embedding or Qdrant failures return **`502`** with a descriptive `detail`.

---

## Catalog attributes

Prefix: `/api/v1/shops/{shop_id}`

Fashion-oriented attribute normalization, alias dictionaries, size charts, and demand signals. Routes exist under both `/fashion/...` and shorter aliases (e.g. `/color-aliases`).

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/fashion/normalize-color` | Member | Normalize a color string. |
| `POST` | `/fashion/normalize-size` | Member | Normalize a size string. |
| `POST` | `/fashion/resolve-variant` | Member | Resolve variant from slots. |
| `POST` | `/variant-resolver/test` | Member | Test variant resolver (alias of above). |
| `GET` | `/color-aliases` | Member | List color aliases. |
| `POST` | `/color-aliases` | Member | Create color alias. `201`. |
| `PATCH` | `/color-aliases/{alias_id}` | Member | Update color alias. |
| `DELETE` | `/color-aliases/{alias_id}` | Member | Delete color alias. `204`. |
| `GET` | `/size-aliases` | Member | List size aliases. |
| `POST` | `/size-aliases` | Member | Create size alias. `201`. |
| `PATCH` | `/size-aliases/{alias_id}` | Member | Update size alias. |
| `DELETE` | `/size-aliases/{alias_id}` | Member | Delete size alias. `204`. |
| `GET` | `/unavailable-demand` | Member | Unavailable SKU demand signals. |
| `GET` | `/fashion/size-charts` | Member | List size charts. |
| `POST` | `/fashion/size-charts` | Member | Create size chart. `201`. |
| `GET` | `/attribute-aliases` | Member | Generic attribute aliases. |
| `POST` | `/attribute-aliases` | Member | Create attribute alias. `201`. |

*(Duplicate `/fashion/color-aliases` and `/fashion/size-aliases` routes mirror the shorter paths.)*

---

## Resolver

Prefix: `/api/v1/resolve`

Deterministic + semantic product/variant resolution with trace storage and operator feedback.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/product` | Authenticated | Resolve product from message text, media refs, context. Body: `ResolveProductRequest`. |
| `POST` | `/variant` | Authenticated | Resolve variant given product candidates and slots. Body: `ResolveVariantRequest`. |
| `GET` | `/{trace_id}` | Member | Get resolver trace. Query: `shop_id`. |
| `POST` | `/{trace_id}/feedback` | Member | Submit operator correction. Query: `shop_id`. Body: `ResolverFeedbackRequest`. |

---

## Semantic search

Prefix: `/api/v1/shops/{shop_id}/semantic-search`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `` | Admin+ (global) | Vector similarity search over catalog. Body: `SemanticSearchRequest`. |

---

## Conversations & customers

### Conversations

Prefix: `/api/v1/shops/{shop_id}/conversations`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `` | Member | List conversations. Filters: `state`, `handoff_required`, `assigned_operator_id`, `unassigned`, `updated_from`, `updated_to`, `search`, `priority_level`, `urgent`, `high_priority`, `needs_attention`, `waiting_for_payment`, `ready_to_order`, `low_confidence`, `is_simulation`, `assigned_to_me`. |
| `GET` | `/{conversation_id}` | Member | Conversation detail + messages. Marks Telegram business read when applicable. |
| `POST` | `/{conversation_id}/messages` | Operator+ | Send manual message (rate limited). Publishes realtime event. |
| `POST` | `/{conversation_id}/send-manual-message` | Operator+ | Alias for manual send (rate limited). |
| `POST` | `/{conversation_id}/take-over` | Operator+ | Operator takes control from agent. |
| `POST` | `/{conversation_id}/response-mode` | Operator+ | Set response mode. Body: `ConversationResponseModeRequest`. |
| `POST` | `/{conversation_id}/release-to-agent` | Operator+ | Return conversation to automation. |
| `POST` | `/{conversation_id}/release-agent` | Operator+ | Alias for release-to-agent. |
| `POST` | `/{conversation_id}/assign` | Operator+ | Assign to operator. Body: `{operator_id}`. |
| `POST` | `/{conversation_id}/mark-resolved` | Operator+ | Mark conversation resolved. |
| `PATCH` | `/{conversation_id}/customer` | Operator+ | Update linked customer from conversation. |
| `POST` | `/{conversation_id}/orders` | Operator+ | Create order from conversation context. `201`. |
| `POST` | `/{conversation_id}/select-product` | Member | Pin selected product on conversation. Body: `{product_id}`. |

### Customers

Prefix: `/api/v1/shops/{shop_id}/customers`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/{customer_id}` | Member | Customer profile. |
| `GET` | `/{customer_id}/preferences` | Member | Customer preferences (auto-created if missing). |
| `PATCH` | `/{customer_id}` | Operator+ | Update customer profile. |

---

## Suggested replies

Prefix: `/api/v1/shops/{shop_id}/suggested-replies`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `` | Member | List pending suggestions. Query: `conversation_id`. |
| `POST` | `/{reply_id}/approve` | Operator+ | Approve and send (rate limited). |
| `POST` | `/{reply_id}/edit-and-send` | Operator+ | Edit text then send (rate limited). |
| `POST` | `/{reply_id}/reject` | Operator+ | Reject suggestion with reason. |

---

## Orders (shop-scoped)

Prefix: `/api/v1/shops`

Legacy/operator order management UI routes. For the canonical state machine, prefer [Order correctness](#order-correctness-canonical-lifecycle).

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/{shop_id}/orders` | Member | List orders. Filters: `status`, `payment_status`, `shipping_status`, `created_from`, `created_to`. |
| `GET` | `/{shop_id}/orders/{order_id}` | Member | Order detail. |
| `POST` | `/{shop_id}/orders/{order_id}/confirm` | Operator+ | Confirm order. |
| `POST` | `/{shop_id}/orders/{order_id}/cancel` | Operator+ | Cancel. Body: `OrderCancelRequest`. |
| `POST` | `/{shop_id}/orders/{order_id}/send-payment-link` | Operator+ | Send payment link. Body: `PaymentLinkRequest`. |
| `POST` | `/{shop_id}/orders/{order_id}/mark-paid` | Operator+ | Manual paid mark. |
| `POST` | `/{shop_id}/orders/{order_id}/stop-recovery` | Operator+ | Stop recovery workflow. |
| `POST` | `/{shop_id}/orders/{order_id}/ship` | Operator+ | Mark shipped. Body: `OrderShipRequest`. |
| `POST` | `/{shop_id}/orders/{order_id}/send-tracking-code` | Operator+ | Send tracking to customer. |

---

## Order correctness (canonical lifecycle)

Prefix: `/api/v1/orders`

State-machine API for draft → clarify → confirm → reserve → payment → complete/cancel. See [order-correctness-architecture.md](./order-correctness-architecture.md).

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/draft` | Authenticated | Create draft order. Body: `OrderDraftCreateRequest`. |
| `POST` | `/{order_id}/clarify` | Operator+ (global) | Request clarification. |
| `POST` | `/{order_id}/confirm` | Operator+ | Confirm line items. |
| `POST` | `/{order_id}/reserve` | Operator+ | Reserve inventory. |
| `POST` | `/{order_id}/payment-link` | Operator+ | Issue payment link. |
| `POST` | `/{order_id}/complete` | Operator+ | Complete order. |
| `POST` | `/{order_id}/cancel` | Operator+ | Cancel with reason. |
| `GET` | `/{order_id}` | Authenticated | Order correctness snapshot. |
| `GET` | `/{order_id}/timeline` | Authenticated | Audit timeline of transitions. |

---

## Recovery & upsells

### Recovery rules

Prefix: `/api/v1/shops/{shop_id}/recovery-rules`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `` | Member | List abandoned-cart / payment recovery rules. |
| `POST` | `` | Operator+ | Create rule. `201`. |
| `PATCH` | `/{rule_id}` | Operator+ | Update rule. |
| `DELETE` | `/{rule_id}` | Operator+ | Delete rule. `204`. |

### Product upsells

Prefix: `/api/v1/shops/{shop_id}/product-upsells`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `` | Member | List upsell rules. |
| `POST` | `` | Operator+ | Create upsell rule. `201`. |
| `PATCH` | `/{upsell_id}` | Operator+ | Update rule. |
| `DELETE` | `/{upsell_id}` | Operator+ | Delete rule. `204`. |

---

## Channels & webhooks

Canonical inbound route: **`POST /api/v1/channels/{provider}/webhook`**

Supported `provider` values: `instagram`, `whatsapp`, `telegram`, `bale`, `rubika` (see `ChannelProvider` enum).

### Channel account management

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/shops/{shop_id}/channels` | Member | List channel accounts. |
| `POST` | `/shops/{shop_id}/channels` | Admin+ | Create channel account. |
| `GET` | `/shops/{shop_id}/channels/{channel_account_id}` | Operator+ | Get account (no secrets). |
| `PATCH` | `/shops/{shop_id}/channels/{channel_account_id}` | Admin+ | Update account metadata. |
| `POST` | `/shops/{shop_id}/channels/{channel_account_id}/credentials` | Admin+ | Save encrypted credentials. |
| `POST` | `/shops/{shop_id}/channels/{channel_account_id}/validate` | Admin+ | Validate credentials with provider. |
| `POST` | `/shops/{shop_id}/channels/{channel_account_id}/webhook-test` | Member | Webhook connectivity test metadata. |

### Webhook verification (GET)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/channels/{provider}/webhook` | Public | Meta-style challenge (`hub.mode`, `hub.verify_token`, `hub.challenge`). |
| `GET` | `/channels/instagram/{channel_account_id}/webhook` | Public | Per-account Instagram verification. |

### Webhook ingestion (POST)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/channels/{provider}/webhook` | Public (signed) | Canonical provider webhook (rate limited). |
| `POST` | `/channels/instagram/{channel_account_id}/webhook` | Public (signed) | Per-account Instagram inbound. |
| `POST` | `/channels/telegram/{channel_account_id}/webhook` | Public (signed) | Per-account Telegram inbound. |
| `POST` | `/channels/telegram/manager/webhook` | Public (secret header) | Platform manager bot (`managed_bot` updates). |
| `POST` | `/webhooks/{provider}` | Public (signed) | Compatibility alias for canonical route. |

**Webhook flow:**

1. Verify signature or secret via provider adapter.
2. Normalize payload to internal message event.
3. Enqueue `channel.message.received` for automation pipeline.
4. Return `WebhookAckResponse` or `WebhookIgnoredResponse`.

See [channels/channel_architecture.md](./channels/channel_architecture.md) and [channels/webhook_security.md](./channels/webhook_security.md).

### Telegram webhook admin

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/shops/{shop_id}/channels/{channel_account_id}/telegram/set-webhook` | Admin+ | Register webhook URL with Telegram. |
| `POST` | `/shops/{shop_id}/channels/{channel_account_id}/telegram/delete-webhook` | Admin+ | Remove webhook. |
| `GET` | `/shops/{shop_id}/channels/{channel_account_id}/telegram/webhook-info` | Member | Current webhook info from Telegram. |

---

## Instagram connect

OAuth-based Instagram Business connection flow.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/shops/{shop_id}/channels/instagram/connect/start` | Admin+ | Start OAuth; returns `authorization_url`, `session_id`. |
| `GET` | `/channels/instagram/oauth/callback` | Public | Meta OAuth callback; redirects to frontend. |
| `GET` | `/shops/{shop_id}/channels/instagram/connect/sessions/{session_id}` | Admin+ | Poll connection session status. |
| `POST` | `/shops/{shop_id}/channels/instagram/connect/sessions/{session_id}/select-account` | Admin+ | Select Meta page/account candidate. |
| `POST` | `/shops/{shop_id}/channels/{channel_account_id}/instagram/reconnect` | Admin+ | Re-run OAuth for existing account. |
| `POST` | `/shops/{shop_id}/channels/{channel_account_id}/disconnect` | Admin+ | Disconnect Instagram account. |
| `GET` | `/shops/{shop_id}/channels/instagram/readiness` | Member | Connection readiness checklist. |

---

## Telegram connect

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/shops/{shop_id}/channels/telegram/connect/start` | Admin+ | Start connect session (BYO bot or managed bot). |
| `GET` | `/shops/{shop_id}/channels/telegram/connect/{session_id}` | Admin+ | Session status. |
| `POST` | `/shops/{shop_id}/channels/telegram/connect/{session_id}/bot-token` | Admin+ | Submit bot token (BYO flow). |
| `POST` | `/shops/{shop_id}/channels/telegram/connect/{session_id}/complete` | Admin+ | Finalize connection → `ChannelAccountRead`. |
| `POST` | `/shops/{shop_id}/channels/telegram/connect/{session_id}/cancel` | Admin+ | Cancel session. |
| `POST` | `/shops/{shop_id}/channels/{channel_account_id}/telegram/business/sync` | Admin+ | Sync Telegram Business connection. |
| `POST` | `/shops/{shop_id}/channels/{channel_account_id}/telegram/business/refresh` | Admin+ | Refresh business connection state. |
| `POST` | `/shops/{shop_id}/channels/{channel_account_id}/telegram/business/validate` | Admin+ | Validate business mode. |
| `POST` | `/shops/{shop_id}/channels/{channel_account_id}/telegram/business/reconnect` | Admin+ | Reconnect business mode. |
| `POST` | `/shops/{shop_id}/channels/{channel_account_id}/telegram/managed-bot/rotate-token` | Admin+ | Rotate managed bot token. |
| `POST` | `/shops/{shop_id}/channels/{channel_account_id}/telegram/managed-bot/reconnect` | Admin+ | Reconnect managed bot. |

---

## Payments (development)

Prefix: `/api/v1/payments`

**Public** mock endpoints for local/staging payment simulation only.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/mock/pay/{payment_id}` | Public | Simulates successful payment; sends confirmation message to conversation. |
| `POST` | `/mock/callback` | Public | Mock gateway callback. Body: `{payment_id, status, provider_reference?}`. |

---

## Agent settings & risk

### Agent studio settings

Prefix: `/api/v1/shops/{shop_id}`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/agent-settings` | Member | Get agent studio settings (alias). |
| `PUT` | `/agent-settings` | Member | Replace agent settings. |
| `GET` | `/agent-studio-settings` | Member | Get agent studio settings. |
| `PATCH` | `/agent-studio-settings` | Member | Partial update. |
| `POST` | `/agent-studio-settings/auto-send-decision` | Member | Evaluate auto-send policy for a draft. |

### Agent risk settings

Prefix: `/api/v1/shops/{shop_id}/agent-risk-settings`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `` | Member | Confidence thresholds and handoff policy. |
| `PUT` | `` | Member | Update risk settings. |

---

## Pilot & pilot mode

### Pilot operations

Prefix: `/api/v1/shops/{shop_id}`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/pilot-settings` | Member | Pilot configuration. |
| `PUT` | `/pilot-settings` | Admin+ | Update pilot settings. |
| `GET` | `/pilot-readiness` | Member | Readiness score. Query: `product_mapping_threshold` (0–1, default 0.8). |
| `POST` | `/pilot/emergency-stop` | Admin+ | Halt automated outbound for shop. |
| `POST` | `/pilot/resume` | Admin+ | Resume after emergency stop. |
| `GET` | `/pilot/metrics` | Member | Pilot KPIs. |
| `GET` | `/pilot/events` | Member | Event log. Query: `limit` (1–200, default 50). |

### Pilot mode (scoped automation)

Prefix: `/api/v1/shops/{shop_id}/pilot-mode`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `PATCH` | `` | Admin+ | Update operating mode / scope. Body: `PilotModeUpdateRequest`. |
| `POST` | `/emergency-stop` | Admin+ | Emergency stop with incident linkage. |

---

## Policies & triggers

### Policy engine

Prefix: `/api/v1/shops/{shop_id}/policies`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/validate` | Member | Evaluate sample action against policy config. |
| `POST` | `/validate-config` | Admin+ | Validate policy JSON schema only. |

### Keyword triggers

Prefix: `/api/v1/shops/{shop_id}/triggers`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `` | Member | List trigger rules. |
| `POST` | `` | Member | Create trigger. `201`. |
| `PATCH` | `/{trigger_id}` | Member | Update trigger. |
| `DELETE` | `/{trigger_id}` | Member | Delete trigger. `204`. |
| `GET` | `/performance` | Member | Trigger performance metrics. |
| `POST` | `/match` | Member | Test keyword match. Body: `TriggerMatchRequest`. |

---

## Social admin & automation

Prefix: `/api/v1/shops/{shop_id}`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/automation-rules` | Member | List automation rule steps (static catalog). |
| `GET` | `/admin-tasks` | Member | List pending admin tasks. |
| `POST` | `/admin-tasks` | Operator+ | Create admin task. `201`. |
| `POST` | `/admin-tasks/{task_id}/approve` | Operator+ | Approve task. |
| `POST` | `/admin-tasks/{task_id}/reject` | Operator+ | Reject task. |
| `GET` | `/operator-corrections` | Member | List operator corrections. |
| `POST` | `/operator-corrections` | Operator+ | Submit correction. `201`. |
| `GET` | `/automation-suggestions` | Member | List suggestions. Query: `status`. |
| `POST` | `/automation-suggestions/{suggestion_id}/approve` | Admin+ | Approve automation suggestion. |
| `POST` | `/automation-suggestions/{suggestion_id}/reject` | Admin+ | Reject suggestion. |

---

## Scenarios & incidents

Prefix: `/api/v1/shops/{shop_id}`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/scenarios` | Admin+ | Create scenario pack for regression testing. |
| `GET` | `/scenarios` | Member | List scenario packs. |
| `GET` | `/incidents` | Member | List incidents. Query: `limit` (default 50). |
| `GET` | `/incidents/{incident_id}` | Member | Incident detail. |
| `GET` | `/scenario-coverage` | Member | Scenario coverage matrix. |
| `POST` | `/scenario-regression/run` | Admin+ | Run social-admin scenario regression. |

---

## Decision traces

| Prefix / path | Description |
|---------------|-------------|
| `/api/v1/shops/{shop_id}/decision-traces` | List agent decision traces for shop |
| `/api/v1/shops/{shop_id}/decision-traces/{trace_id}` | Single trace |
| `/api/v1/shops/{shop_id}/conversations/{conversation_id}/decision-traces` | Traces for one conversation |
| `/api/v1/shops/{shop_id}/traces/{trace_id}` | Assembled decision trace (enriched) |

All require **Member** auth.

---

## Analytics

Prefix: `/api/v1/shops/{shop_id}/analytics`

All endpoints accept optional date range query params (`date_from`, `date_to`, `start`, `end`) and require **Member** auth.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/funnel` | Conversion funnel metrics |
| `GET` | `/posts` | Post performance rows |
| `GET` | `/post-revenue` | Revenue attributed to posts |
| `GET` | `/stock-demand` | Stock vs demand signals |
| `GET` | `/handoff` | Handoff analytics |
| `GET` | `/unavailable-demand` | Unavailable SKU demand |
| `GET` | `/lost-demand` | Lost demand (paginated: `page`, `page_size`) |
| `GET` | `/operator-performance` | Operator metrics (paginated) |
| `GET` | `/agent-performance` | Agent automation metrics |
| `GET` | `/response-time` | Response time distribution |

See [analytics-guide.md](./analytics-guide.md).

---

## Simulator & TRL validation

### DM simulator

Prefix: `/api/v1/shops/{shop_id}/simulator`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/run` | Member | Run DM simulation turn. Body: `DMSimulatorRequest`. |
| `POST` | `/replay` | Admin+ | Batch replay against scenario. |
| `GET` | `/runs` | Member | List runs. Query: `legacy` (bool). |
| `GET` | `/runs/{run_id}` | Member | Run detail with items. |
| `DELETE` | `/reset` | Member | Delete simulation conversations. |

See [simulator-guide.md](./simulator-guide.md).

### TRL validation

Prefix: `/api/v1/shops/{shop_id}/trl-validation`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/run` | Member | Start validation run. Body: `TRLValidationRunRequest`. |
| `GET` | `/runs` | Member | List runs. |
| `GET` | `/runs/{run_id}` | Member | Run detail. |
| `GET` | `/runs/{run_id}/scenarios` | Member | Scenario results. Query: `passed`. |
| `GET` | `/runs/{run_id}/risk-metrics` | Member | Aggregated risk metrics. |
| `DELETE` | `/reset` | Member | Reset demo validation data. |

---

## Failed jobs

### Shop-scoped

Prefix: `/api/v1/shops/{shop_id}/failed-jobs` — requires **Admin+**

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `` | List failed jobs (paginated, filterable by `status`, `queue_name`, `job_type`, dates) |
| `POST` | `/{job_id}/retry` | Re-enqueue job |
| `POST` | `/{job_id}/ignore` | Mark ignored |

### Platform (cross-shop)

Prefix: `/api/v1/failed-jobs` — lists jobs across shops the user can access

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `` | List jobs. Query: `shop_id`, `unscoped_only`, pagination, filters |
| `POST` | `/{job_id}/retry` | Retry |
| `POST` | `/{job_id}/ignore` | Ignore |

See [failed-jobs-runbook.md](./failed-jobs-runbook.md).

---

## Related documentation

| Topic | Document |
|-------|----------|
| Admin UI screens & redesign | [ui-design-guide.md](./ui-design-guide.md) |
| Documentation index | [README.md](./README.md) |
| Catalog indexing & resolver design | [catalog-intelligence-architecture.md](./catalog-intelligence-architecture.md) |
| Order state machine | [order-correctness-architecture.md](./order-correctness-architecture.md) |
| Channel adapters & webhooks | [channels/channel_architecture.md](./channels/channel_architecture.md) |
| Provider setup | [channels/provider_onboarding.md](./channels/provider_onboarding.md) |
| Webhook security | [channels/webhook_security.md](./channels/webhook_security.md) |
| Environment variables | [environment-variables.md](./environment-variables.md) |
| Local setup | [setup.md](./setup.md) |
| Operator workflows | [operator-guide.md](./operator-guide.md) |

---

## Maintaining this document

Route definitions live in `backend/app/api/v1/`. When adding endpoints:

1. Register the router in `backend/app/api/v1/router.py`.
2. Add Pydantic schemas with field descriptions (surfaces in OpenAPI).
3. Update this guide and the relevant architecture doc.
4. Run `pytest app/tests` for affected modules.

For schema-level accuracy, prefer **`/docs`** or **`/openapi.json`** over duplicating every field here.
