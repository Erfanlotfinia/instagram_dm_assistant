# Instagram DM Assistant

This repository is an advanced MVP for an Instagram DM ordering agent. It includes a FastAPI backend, PostgreSQL schema and Alembic migrations, RabbitMQ/Redis/Qdrant integrations, an OpenAI-powered conversation orchestrator, background workers, and a React TypeScript admin panel for shops, products, conversations, and orders.

## Architecture

```text
.
├── backend/                 # FastAPI service and Python project metadata
│   ├── app/
│   │   ├── api/v1/          # Versioned API routers only
│   │   ├── core/            # Settings, logging, errors, security, pagination
│   │   ├── db/              # SQLAlchemy session, base metadata, Alembic migrations
│   │   ├── domain/          # Future domain models and domain logic
│   │   ├── services/        # Future application services
│   │   ├── integrations/    # Future external service adapters
│   │   ├── workers/         # Future background consumers/producers
│   │   ├── schemas/         # Future Pydantic request/response schemas
│   │   ├── repositories/    # Future persistence adapters
│   │   └── tests/           # Pytest suite
│   ├── alembic.ini
│   └── pyproject.toml
├── frontend/                # Vite React TypeScript admin app
│   ├── src/app/             # App shell, global styles, test setup
│   ├── src/components/      # Reusable UI components
│   ├── src/pages/           # Page-level components
│   ├── src/services/        # API client setup
│   ├── src/types/           # Shared frontend types
│   ├── src/hooks/           # React hooks
│   └── src/routes/          # Route definitions
├── docker-compose.yml       # Local multi-service stack
└── .env.example             # Required environment variable template
```

## Services

Docker Compose starts the following services:

- `backend`: FastAPI API server on <http://localhost:8000> (runs Alembic migrations before startup)
- `frontend`: Vite admin app on <http://localhost:5173>
- `postgres`: PostgreSQL database on `localhost:5432`
- `redis`: Redis cache/broker support on `localhost:6379`
- `rabbitmq`: RabbitMQ on `localhost:5672`, management UI on <http://localhost:15672>
- `qdrant`: Qdrant vector database on <http://localhost:6333>

Postgres, Redis, RabbitMQ, and Qdrant include container health checks so dependent services wait for infrastructure readiness.

## Environment variables

Copy the example file before starting the stack:

```bash
cp .env.example .env
```

Required backend variables:

- `DATABASE_URL` — PostgreSQL connection string.
- `REDIS_URL` — Redis connection string for locks, rate limits, and state support.
- `RABBITMQ_URL` — RabbitMQ AMQP URL for inbound message jobs.
- `QDRANT_URL` — Qdrant API URL for product semantic search.
- `OPENAI_API_KEY` — OpenAI API key used by the LLM and embedding integrations.
- `APP_ENV` / `LOG_LEVEL` — runtime environment and logging level.
- `JWT_SECRET_KEY` — at least 32 random bytes recommended in production.
- `TOKEN_ENCRYPTION_KEY` — secret used to derive the Fernet key for Instagram token encryption.
- `INSTAGRAM_WEBHOOK_VERIFY_TOKEN` / `INSTAGRAM_APP_SECRET` — Meta webhook verification and optional signature validation.

Frontend uses `VITE_API_BASE_URL` to target the backend from the browser.

## Local setup with Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

Useful commands:

```bash
docker compose ps
docker compose logs -f backend
docker compose logs -f worker
docker compose exec backend python -m app.scripts.seed
docker compose exec backend python -m app.scripts.seed_demo_data
docker compose down
docker compose down -v
```

Health endpoints:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/ready
```

## Backend development

From the `backend/` directory:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
alembic upgrade head
python -m app.scripts.seed
python -m app.scripts.seed_demo_data
uvicorn app.main:app --reload
```

### Demo credentials (local development only)

After seeding:

- Email: `admin@example.com`
- Password: `changeme123`
- Demo shop slug: `demo-shop`

Use **Onboarding** and **DM Simulator** in the admin panel to verify setup before enabling auto-replies.

Run backend tests:

```bash
cd backend
pytest
```

Run backend linting:

```bash
cd backend
ruff check .
```

## Database migrations

Alembic is configured under `backend/app/db/migrations` and uses `DATABASE_URL` from the environment.

Apply migrations inside the backend container:

```bash
docker compose exec backend alembic upgrade head
docker compose exec backend alembic downgrade -1  # only when safe for your local data
docker compose exec backend alembic upgrade head
```

Create a future migration after adding SQLAlchemy models:

```bash
docker compose exec backend alembic revision --autogenerate -m "describe change"
```

For local development outside Docker:

```bash
cd backend
alembic upgrade head
```

## Frontend development

From the `frontend/` directory:

```bash
npm install
npm run dev
```

Run frontend checks:

```bash
cd frontend
npm run typecheck
npm run lint
npm test
npm run build
```

## Implementation notes

- API routers remain thin and expose only HTTP boundaries.
- Cross-cutting concerns live in `backend/app/core`.
- Structured JSON logging is configured at application startup for container-friendly log ingestion.
- Global exception handlers normalize API error responses.
- CORS allows the local Vite frontend origin by default.
- Instagram webhook ingestion stores raw payloads and uses message IDs for idempotency.
- RabbitMQ workers serialize conversation processing with Redis locks.
- The LLM only extracts structured intent/slots; services validate products, variants, prices, inventory, payments, and state transitions.
- Orders require explicit customer confirmation before payment and cannot be marked paid by the LLM.

## Meta Instagram webhook setup

Configure these backend environment variables:

- `INSTAGRAM_WEBHOOK_VERIFY_TOKEN` — shared secret used during Meta webhook verification
- `ENABLE_REAL_INSTAGRAM_SEND` — keep `false` locally unless you are ready to call the real Graph API
- `CONVERSATION_LOCK_TTL_SECONDS` — Redis lock TTL for per-conversation worker serialization

Webhook endpoints exposed by the API:

- `GET /api/v1/webhooks/instagram` — Meta challenge verification
- `POST /api/v1/webhooks/instagram` — inbound Instagram messaging events

### Local development with ngrok

1. Start the stack: `docker compose up --build`
2. Expose the backend: `ngrok http 8000`
3. In the Meta developer dashboard, create a webhook subscription for your Instagram app:
   - Callback URL: `https://<your-ngrok-host>/api/v1/webhooks/instagram`
   - Verify token: same value as `INSTAGRAM_WEBHOOK_VERIFY_TOKEN`
4. Subscribe to `messages` (and related messaging fields you need).
5. Connect an Instagram business account in the admin UI and ensure its `ig_user_id` matches the webhook `recipient.id`.

### Processing pipeline

1. Webhook stores the full raw payload in `webhook_events`.
2. Matching `instagram_accounts` are resolved by recipient Instagram user ID.
3. Customers, conversations, and inbound messages are created or updated.
4. A job is published to RabbitMQ queue `instagram.message.received`.
5. The `worker` service consumes jobs, acquires a Redis lock per conversation, runs orchestration, logs agent decisions/actions, stores outbound messages, and marks the webhook event processed.

Run the worker locally:

```bash
docker compose up worker
```

Run the scheduler locally:

```bash
docker compose up scheduler
```

Or outside Docker:

```bash
cd backend
python -m app.workers.main
```

## Sprint 6 manual QA checklist

Use this checklist after `docker compose up --build` and seeding a demo shop.

### Authentication & shell

- [ ] Sign in with email/password; invalid input shows field-level validation errors
- [ ] JWT persists across page refresh; sign out clears session
- [ ] Sidebar shows selected shop name; shop selection persists across pages

### Dashboard

- [ ] Metrics load for selected shop: today orders, paid, waiting for payment, handoffs
- [ ] Conversion funnel shows inbound → product resolved → draft → paid counts
- [ ] Low-stock variants list links to product detail

### Conversations

- [ ] List filters by state, handoff, date, and customer search
- [ ] Detail shows message timeline, slots, linked product/order, agent actions
- [ ] Take over → send manual message → release to agent workflow works
- [ ] Mark resolved closes conversation; customer details can be edited
- [ ] Create order from conversation when slots are complete

### Products & mapping

- [ ] Product list supports search and pagination; low-stock products are flagged
- [ ] Product detail shows variant stock with low-stock warnings
- [ ] Instagram mapping: paste URL, select product, save manual map
- [ ] Test resolve shows match; confirm semantic match creates mapping

### Orders

- [ ] Order list filters and pagination work
- [ ] Order detail: confirm, mark paid, ship (with tracking), cancel use confirmation dialogs
- [ ] Toast notifications appear for success and error actions

### Settings

- [ ] Shop profile can be updated (name, currency)
- [ ] Instagram account and webhook status display correctly
- [ ] Agent settings save: auto reply, confidence thresholds, handoff mode, Persian default language

### RTL & responsive

- [ ] Layout remains usable on mobile viewport (< 900px)
- [ ] Setting `dir="rtl"` on `<html>` mirrors message bubbles and table alignment

## Sprint 7: Security, observability, and production readiness

### Security

- Redis rate limiting on login, webhook, and outbound message endpoints
- Request ID middleware (`X-Request-ID`) and secure response headers
- Audit logging for login, product CRUD, inventory changes, order status, manual payment, handoff take/release
- Instagram access tokens encrypted at rest (Fernet)
- Sensitive data masked in structured JSON logs
- Shop membership checks on shop-scoped API routes
- Optional Meta webhook signature verification (`INSTAGRAM_APP_SECRET`)
- Production CORS configuration via `CORS_ORIGINS`

### Observability

- Structured JSON logs with `request_id` correlation
- Prometheus metrics at `GET /api/v1/metrics`
- Readiness probe at `GET /api/v1/ready` (postgres, redis, rabbitmq, qdrant)

### Reliability

- RabbitMQ retry queue + DLQ with configurable max retries
- Idempotency: webhook message ID, payment callback reference, order confirmation
- Background scheduler: expire unpaid orders, refresh product embeddings
- Graceful worker shutdown on SIGINT/SIGTERM

### Documentation

See the `docs/` folder:

- [Production deployment](docs/production-deployment.md)
- [Environment variables](docs/environment-variables.md)
- [Meta webhook setup](docs/meta-webhook-setup.md)
- [Operator guide](docs/operator-guide.md)
- [Admin guide](docs/admin-guide.md)
- [Troubleshooting](docs/troubleshooting.md)
- [API reference](docs/api.md)
- [Demo scenario](docs/demo-scenario.md)

### Run tests

```bash
cd backend && pytest
cd frontend && npm test
```

### Health and metrics

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/ready
curl http://localhost:8000/api/v1/metrics
```


## Competitive positioning

This product is not a generic social-media chatbot. It is a specialized Instagram Fashion Order Agent for online fashion shops. The differentiation is deterministic backend control around Instagram post-to-product mapping, Persian/English color normalization, size normalization, SKU/variant resolution, inventory validation, explicit order confirmation, payment callback safety, human handoff, operator preview, decision audit trails, and conversion analytics.

### Demo: Persian fashion DM order

Customer sends: `این کارو مشکی سایز L می‌خوام`

Expected flow:

1. Instagram post maps to product, or a multi-product post asks the customer which item they mean.
2. Color `مشکی` normalizes to `black`; size `L` normalizes to `L`.
3. Backend `VariantResolver` resolves SKU and stock; the LLM only extracts raw slots.
4. Missing customer information is requested, then a draft order is created.
5. Customer explicitly confirms; only then is payment initiated.
6. Idempotent payment callback marks the order paid once and inventory is not reduced/reserved twice.
7. Admin sees current state, slots, selected product/variant, alternatives, confidence, suggested reply, and full audit trail.

### Local development

```bash
docker compose up -d postgres redis rabbitmq qdrant
cd backend && alembic upgrade head && uvicorn app.main:create_app --factory --reload
cd frontend && npm install && npm run dev
```

Key admin pages: `/onboarding`, `/simulator`, `/analytics`, `/instagram-mapping`, `/conversations`, `/orders`.


## Competitor-informed positioning

This is not a generic chatbot. It is an Instagram-first fashion order agent that turns social interactions into accurate, payable, shippable orders. The architecture now keeps Instagram parsing inside integrations while the order core consumes channel-independent messages, making WhatsApp, Telegram, and Web Chat future-ready.

Key differentiators versus Meta Business Agent, Manychat, Chatfuel, Gorgias, SleekFlow, Inrō, Respond.io, and Tidio:

- Instagram post-to-product/SKU mapping, including multi-product posts.
- Deterministic color and size normalization for fashion variants.
- Inventory validation and unavailable-demand tracking before order/payment actions.
- Comment/story/reel/ad trigger rules that continue into the normal order flow.
- Agent Studio controls for auto-send, previews, brand voice, selling style, discount policy, and handoff.
- Safe agent decision traces and a DM Simulator for test conversations.
- Fashion/order analytics for funnel, post conversion, unavailable demand, handoff, and response time.

See `docs/competitor-research-mvp.md` for the detailed demo scenario and operator guide.
