# Modira — AI Social Media Admin OS

Modira is an **AI Social Media Admin OS** for online shops. It automates sales, support, order operations, and customer communication across social channels through one unified inbox and one channel-agnostic automation core.

Supported channels:

- Instagram
- WhatsApp
- Telegram
- Bale
- Rubika

Modira is not a single-channel chatbot. Channel adapters normalize inbound events, deterministic services own commerce and policy decisions, and the LLM is used only as a safe fallback for ambiguity.

## Product philosophy

```text
Automation First → Catalog and Commerce Rules → Scenario Routing → LLM Fallback → Human Handoff
```

The safety boundary is intentional:

- Deterministic automation handles known scenarios first.
- Catalog, order, payment, and shipping services own business state.
- Scenario routing selects approved handlers and escalation paths.
- LLM fallback can classify ambiguity or draft safe text, but it cannot set prices, set stock, finalize payment, finalize order state, bypass policies, or mutate inventory.
- Human handoff is the final safety layer for complaints, payment disputes, low confidence, policy-sensitive requests, and explicit operator requests.

## Core capabilities

- Unified inbox across Instagram, WhatsApp, Telegram, Bale, and Rubika.
- AI-powered conversation handling for product questions, sales, support, returns, complaints, and follow-ups.
- Automation-first scenario engine with deterministic handlers and regression coverage.
- Product catalog understanding for generic online shops, not a single vertical.
- Referenced-content resolution for phrases such as “this”, “that one”, “second product”, “same as before”, story/post/reel references, and forwarded content.
- Order creation and management through existing order services and state transitions.
- Payment and shipping flows guarded by deterministic business rules.
- Human handoff workflows for operators and admins.
- Admin dashboard for analytics, controls, system health, failed jobs, pilot readiness, and scenario simulation.
- Scenario simulation and replay tooling for safe testing before production rollout.

## Architecture overview

```text
┌─────────────────────────────────────────────────────────────────────┐
│                         Channel Adapter Layer                        │
├──────────────┬──────────────┬──────────────┬──────────┬─────────────┤
│ Instagram    │ WhatsApp     │ Telegram     │ Bale     │ Rubika      │
│ Adapter      │ Adapter      │ Adapter      │ Adapter  │ Adapter     │
└──────┬───────┴──────┬───────┴──────┬───────┴────┬─────┴──────┬──────┘
       │              │              │            │            │
       └──────────────┴──────────────┴────────────┴────────────┘
                              │
                              ▼
                    NormalizedMessage
       channel, user_id, conversation_id, message_type,
       content, attachments, metadata
                              │
                              ▼
                Unified Inbox / Message Event System
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                            Core Engine                              │
├─────────────────────────────────────────────────────────────────────┤
│ 1. ConversationContextGraph / ConversationContextService             │
│ 2. AutomationEngine + AutomationHandlerRegistry                      │
│ 3. CatalogQueryPlanner + ProductDiscoveryService + CatalogService    │
│ 4. ScenarioRouter                                                    │
│ 5. OrderService / PaymentService / ShippingService                   │
│ 6. LLMFallbackOrchestrator                                           │
│ 7. HumanHandoffService                                               │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        Admin dashboard, analytics, scenario simulator, operators
```

### Normalized message contract

All channel adapters should normalize inbound updates into the same core envelope before invoking the social admin engine:

```text
NormalizedMessage
├── channel
├── user_id
├── conversation_id
├── message_type
├── content
├── attachments
└── metadata
```

Provider-specific payloads remain available in metadata for auditability, idempotency, and advanced routing, but business logic must consume normalized fields wherever possible.

## Generic product domain

Modira supports any online shop category, including electronics, tools, cosmetics, furniture, services, digital products, food, books/media, home goods, and other catalog-driven shops.

The generic product view is:

```text
GenericProduct
├── product_id
├── title
├── description
├── category
├── attributes          # key-value product facts
├── variants            # option sets, SKU, price, stock
├── price
├── stock
├── media
└── availability_rules
```

Existing product and variant tables are preserved. Compatibility fields are adapted into generic attributes so current order and payment logic continues to work while new categories can be modeled without vertical-specific assumptions.

## Repository layout

```text
.
├── backend/                 # FastAPI service and Python project metadata
│   ├── app/
│   │   ├── api/v1/          # Versioned API routers and HTTP boundaries
│   │   ├── channels/        # Provider adapters and channel abstractions
│   │   ├── core/            # Settings, logging, errors, security, pagination
│   │   ├── db/              # SQLAlchemy session, base metadata, migrations
│   │   ├── domain/          # SQLAlchemy models and domain enums
│   │   ├── integrations/    # External service integrations
│   │   ├── repositories/    # Persistence adapters
│   │   ├── schemas/         # Pydantic request/response/core schemas
│   │   ├── services/        # Core orchestration and business services
│   │   ├── workers/         # Background consumers and scheduled jobs
│   │   └── tests/           # Pytest suite
│   ├── alembic.ini
│   └── pyproject.toml
├── frontend/                # Vite React TypeScript admin app
│   ├── src/app/             # App shell, global styles, test setup
│   ├── src/components/      # Reusable UI components
│   ├── src/pages/           # Dashboard and page-level views
│   ├── src/services/        # API client setup
│   ├── src/types/           # Shared frontend types
│   ├── src/hooks/           # React hooks
│   └── src/routes/          # Route definitions
├── landing/                 # Marketing / landing app
├── docs/                    # Operational, deployment, API, and architecture docs
├── scripts/                 # Local verification and smoke-test scripts
├── docker-compose.yml       # Local multi-service stack
└── .env.example             # Environment variable template
```

## Important backend modules

- `backend/app/channels/` — multi-channel provider adapter layer.
- `backend/app/schemas/channels.py` — channel schemas, including `NormalizedInboundMessage`, `NormalizedOutboundMessage`, and `NormalizedMessage`.
- `backend/app/services/social_admin/scenario_router.py` — scenario routing for automation-first handling.
- `backend/app/services/social_admin/handlers.py` — deterministic automation handler registry and handlers.
- `backend/app/services/social_admin/context_graph.py` — conversation context graph and referenced-content resolution.
- `backend/app/services/social_admin/catalog_query_planner.py` — catalog query planning.
- `backend/app/services/social_admin/product_discovery_service.py` — generic product discovery view.
- `backend/app/services/social_admin/llm_fallback_orchestrator.py` — structured, safety-constrained LLM fallback validation.
- `backend/app/services/social_admin/human_handoff_service.py` — explicit final human escalation service.
- `backend/app/services/order_service.py` — order lifecycle and state transitions.
- `backend/app/services/payment_service.py` — payment safety and payment-state operations.
- `backend/app/services/shipping_service.py` — shipping methods, tracking, and fulfillment operations.

## Services in Docker Compose

Docker Compose starts the following services:

- `backend`: FastAPI API server on <http://localhost:8800> (container port 8000; applies migrations before startup).
- `worker`: RabbitMQ consumer for inbound message processing.
- `scheduler`: periodic background jobs such as outbox publishing and retention work.
- `frontend`: Vite admin app on <http://localhost:5173>.
- `postgres`: PostgreSQL database on `localhost:5432`.
- `redis`: Redis cache, lock, rate-limit, and state support on `localhost:6379`.
- `rabbitmq`: RabbitMQ on `localhost:5672`, management UI on <http://localhost:15672>.
- `qdrant`: Qdrant vector database on <http://localhost:6333>.

Postgres, Redis, RabbitMQ, and Qdrant include health checks so dependent services can wait for infrastructure readiness.

## Environment variables

Copy the example file before starting the stack:

```bash
cp .env.example .env
```

Common backend variables:

- `DATABASE_URL` — PostgreSQL connection string.
- `REDIS_URL` — Redis connection string for locks, rate limits, and state support.
- `RABBITMQ_URL` — RabbitMQ AMQP URL for inbound message jobs.
- `QDRANT_URL` — Qdrant API URL for product semantic search.
- `LLM_MODE` — `mock` for deterministic local/test mode or `live` for provider-backed calls.
- `LLM_PROVIDER` — configured LLM provider.
- `OPENAI_API_KEY` / `OPENAI_API_BASE_URL` / `OPENAI_MODEL` — OpenAI-compatible provider settings.
- `GEMINI_API_KEY` / `GEMINI_MODEL` — Gemini provider settings.
- `OPENAI_EMBEDDING_MODEL` / `GEMINI_EMBEDDING_MODEL` — embedding model configuration.
- `APP_ENV` / `LOG_LEVEL` — runtime environment and log level.
- `JWT_SECRET_KEY` — at least 32 random bytes recommended in production.
- `TOKEN_ENCRYPTION_KEY` — secret used to derive the Fernet key for provider credential encryption.
- Provider webhook secrets and tokens — Meta/Instagram, WhatsApp, Telegram, Bale, and Rubika credentials. Tokens are encrypted at rest and must never be returned raw by APIs.
- `WEBHOOK_INTERNAL_SECRET` / `META_APP_SECRET` — Meta webhook verification and signature validation for Instagram/Meta channels.

Frontend uses `VITE_API_BASE_URL` to target the backend from the browser.

See [docs/environment-variables.md](docs/environment-variables.md) for the complete list.

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
curl http://localhost:8800/health
curl http://localhost:8800/ready
curl http://localhost:8800/api/v1/health
curl http://localhost:8800/api/v1/ready
curl http://localhost:8800/api/v1/metrics
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

Run backend tests:

```bash
cd backend
pytest
```

Run backend linting:

```bash
cd backend
ruff check .
ruff format .
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

## Database migrations

Alembic is configured under `backend/app/db/migrations` and uses `DATABASE_URL` from the environment.

Apply migrations inside the backend container:

```bash
docker compose exec backend alembic upgrade head
docker compose exec backend alembic downgrade -1  # only when safe for local data
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

## Webhooks and inbound processing

The current production-compatible Meta endpoints remain available for Instagram/Meta traffic, while the channel foundation supports additional provider adapters.

Webhook endpoints include:

- `GET /api/v1/webhooks/instagram` — Meta challenge verification.
- `POST /api/v1/webhooks/instagram` — inbound Instagram messaging events.
- `POST /api/v1/webhooks/meta` — Meta webhook alias with idempotent ingestion.
- Provider-specific channel webhook routes under the channel API layer where configured.

Processing pipeline:

1. Webhook ingestion stores the raw payload and idempotency keys.
2. A channel adapter parses the provider payload.
3. Provider fields are normalized into the shared message schemas.
4. Customers, conversations, and inbound messages are created or updated.
5. A background job is published for worker processing.
6. The worker acquires a Redis lock per conversation, runs the Modira core engine, records decisions/actions, stores outbound messages, and marks the webhook event processed.

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

## Safety guarantees

- API routers remain thin and expose only HTTP boundaries.
- Channel-specific parsing stays inside adapters and integrations.
- Business logic belongs in channel-agnostic services.
- RabbitMQ workers serialize conversation processing with Redis locks.
- Idempotency is enforced for webhook messages, payment callbacks, and order confirmation flows.
- The LLM only extracts structured ambiguity signals and safe drafts; services validate products, variants/options, prices, inventory, payments, shipping, and order state transitions.
- Orders require explicit customer confirmation before payment.
- Payment status cannot be marked paid by the LLM.
- Admin content generation remains draft-first and approval-gated.
- Signed callback actions reject forged, expired, or cross-shop payloads.

## Admin and operator workflows

The admin dashboard is used for:

- Inbox triage and operator handoff.
- Conversation details, state, slots, linked product/order, and audit trail.
- Catalog management and product discovery controls.
- Order management, payment review, shipping updates, and cancellation.
- Analytics for funnel, handoff, unavailable demand, response time, and system health.
- Scenario simulation, regression replay, pilot readiness, and emergency controls.
- Automation rules, operator corrections, and approval-gated admin AI tasks.

## CI and verification

GitHub Actions and local verification scripts are expected to cover:

- Backend linting and tests.
- Alembic migration checks.
- Scenario regression and replay suites.
- Frontend typecheck, lint, tests, and build.
- Docker smoke checks for backend readiness and frontend availability.

One-shot local gate, assuming Postgres and Redis are available on default ports:

```bash
# Linux / macOS / Git Bash
bash scripts/verify_local.sh

# Windows PowerShell
powershell -File scripts/verify_local.ps1
```

Individual checks:

```bash
# Backend
cd backend && ruff check . && pytest app/tests -q
bash scripts/check_migrations.sh

# Frontend
cd frontend && npm run typecheck && npm run lint && npm test && npm run build

# Full stack smoke, requires Docker
bash scripts/docker_smoke_test.sh
powershell -File scripts/docker_smoke_test.ps1
```

## Documentation index

- [API reference](docs/api.md)
- [API documentation](docs/api-documentation.md)
- [Environment variables](docs/environment-variables.md)
- [Production deployment](docs/production-deployment.md)
- [Security configuration](docs/security_configuration.md)
- [Production incident response](docs/production_incident_response.md)
- [Migration guide](docs/migration-guide.md)
- [Failed jobs runbook](docs/failed-jobs-runbook.md)
- [Analytics guide](docs/analytics-guide.md)
- [Operator guide](docs/operator-guide.md)
- [Admin guide](docs/admin-guide.md)
- [Simulator guide](docs/simulator-guide.md)
- [Catalog intelligence architecture](docs/catalog-intelligence-architecture.md)
- [Order correctness architecture](docs/order-correctness-architecture.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Retention and deletion](docs/retention-deletion.md)
- [Pilot readiness](docs/sprint-f-pilot-readiness.md)

## Production readiness notes

Before admitting real customer traffic:

- Configure encrypted provider credentials and webhook secrets for each enabled channel.
- Verify real-provider sandbox behavior for WhatsApp, Telegram, Bale, and Rubika.
- Keep emergency-stop procedures tested and documented.
- Confirm database migrations on a clean environment.
- Run scenario regression and webhook idempotency tests.
- Review CORS, rate limits, audit logging, token encryption, structured log masking, and membership checks.
- Validate payment provider callbacks and shipping-provider integrations with idempotent references.
- Ensure operators understand handoff, takeover, release, and manual message workflows.
