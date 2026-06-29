# AGENTS.md

Engineering guide for AI coding agents working in this repository.

## Project overview

**Modira Enterprise Admin OS** is a multi-channel commerce operator platform. It centralizes inbound customer messages, catalog-aware automation, human handoff, analytics, and system operations across Instagram, WhatsApp, Telegram, Bale, and Rubika.

### Channel architecture

All providers follow the same adapter contract:

1. Verify the webhook signature
2. Normalize provider payloads into a generic message-received event
3. Enqueue `channel.message.received`
4. Run automation-first execution
5. Send outbound replies through the provider adapter

Canonical webhook route: `/api/v1/channels/{provider}/webhook`

### Execution model

Automation rules, deterministic catalog resolution, order state transitions, and policy gates run before any model fallback. LLM fallback is bounded to extraction, classification, or drafting when deterministic logic cannot resolve safely. Risky, ambiguous, policy-sensitive, or customer-impacting actions require preview or human handoff.

### Catalog model

Catalog attributes are generic key/value facts scoped by shop, category, and aliases. Clothing color and size are supported as ordinary attributes rather than product-wide architecture assumptions.

## Repository layout

| Path | Role |
|------|------|
| `backend/` | FastAPI API, workers, migrations, tests |
| `frontend/` | React admin app (Vite) |
| `landing/` | Standalone RTL marketing site |
| `docs/` | Operator, UI design, migration, TRL, channel docs — start at `docs/README.md` |
| `docker/` | Docker-related assets |
| `infra/` | Infrastructure config |
| `scripts/` | Local verify, migration check, Docker smoke |
| `docker-compose.yml` | Full stack dev/prod compose |
| `.env.example` | Env template (never commit real `.env`) |

## Backend

### Stack

- Python 3.12+, FastAPI, SQLAlchemy 2, Alembic, Pydantic Settings
- PostgreSQL (`psycopg`), Redis, RabbitMQ (`pika`), Qdrant
- OpenAI / Gemini adapters for LLM and embeddings
- Tooling: pytest, pytest-asyncio, ruff

### Important folders

Under `backend/app/`:

| Folder | Purpose |
|--------|---------|
| `api/` | FastAPI routes (`api/v1/`) |
| `core/` | Config, security, logging, CSRF, metrics |
| `db/migrations/` | Alembic revisions (`alembic.ini` → `script_location = app/db/migrations`) |
| `domain/` | SQLAlchemy models and enums |
| `repositories/` | Data access layer |
| `services/` | Business logic (orders, webhooks, audit, channels, social admin) |
| `integrations/` | Provider adapters, webhook signatures, Redis, Qdrant |
| `workers/` | RabbitMQ consumers and scheduler |
| `tests/` | pytest suite (`testpaths = app/tests`) |
| `scripts/` | Seed data, benchmarks, regression runners |

### Install

```bash
cd backend
pip install -e ".[dev]"
```

### Run tests

**Prerequisites:** PostgreSQL on `localhost:5432` (test DB `modira_test`), Redis, and RabbitMQ for the full suite. `conftest.py` remaps Docker hostnames (`postgres` → `localhost`) when not running inside a container.

```bash
cd backend
pytest app/tests -q --tb=short          # full suite (matches CI)
pytest app/tests/test_health.py -q      # single file
pytest -m integration                   # DB + migration integration tests
ruff check app                          # lint
```

Test env is auto-set in `conftest.py`: `WEBHOOK_SIGNATURE_BYPASS=true`, `LLM_MODE=mock`, `APP_ENV=development`.

**Full local verify** (from repo root):

```bash
bash scripts/verify_local.sh
```

## Frontend

### Stack

- React, TypeScript, Vite, Tailwind CSS v4
- TanStack Query, Zustand, React Hook Form + Zod, Recharts
- Vitest + Testing Library; Playwright for e2e

### Important folders

Under `frontend/src/`:

| Folder | Purpose |
|--------|---------|
| `pages/`, `routes/` | Route-level views |
| `components/` | UI (shell, conversations, catalog, channels, trust, orders) |
| `contexts/`, `stores/` | Auth, shop, theme state |
| `services/` | `apiClient` (cookie auth + CSRF), realtime |
| `lib/`, `hooks/`, `types/` | Shared utilities and types |

### Commands (admin app)

```bash
cd frontend
npm ci
npm run typecheck    # tsc -b
npm run lint         # same as typecheck (no ESLint)
npm test             # vitest run
npm run test:e2e     # playwright (optional)
npm run build        # tsc -b && vite build
npm run dev          # Vite dev server (port 5173)
```

### Landing site

Separate Vite React 18 marketing site in `landing/`. Copy lives in `landing/src/content/site.ts`. No test script in `package.json`.

```bash
cd landing
npm ci
npm run typecheck
npm run build
npm run dev          # port 5174
```

See `landing/README.md` for editing brand copy, CTAs, and Docker port mapping.

## Migrations

Alembic migrations live in `backend/app/db/migrations/`.

**Docker:**

```bash
docker compose exec backend alembic upgrade head
```

The backend container also runs `alembic upgrade head` before Uvicorn starts.

**Local shell** (use `localhost` host, not `postgres`):

```bash
cd backend
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/modira alembic upgrade head
```

**Validation:**

```bash
bash scripts/check_migrations.sh   # from repo root
cd backend && alembic heads        # confirm single head
```

Rules:

1. Run `alembic heads` and confirm a single head before merging schema changes.
2. Run `alembic upgrade head` against a clean PostgreSQL database.
3. Run backend tests that cover migrations and order/payment transitions.
4. Never run production migrations without a database backup and rollback plan.

See `docs/migration-guide.md` for more detail.

## Dev environment quick start

```bash
cp .env.example .env
docker compose up backend frontend
```

Further setup: `docs/migration-guide.md`, `docs/troubleshooting.md`, `landing/README.md`.

## Coding conventions

### Backend

- Ruff: line length 100, target py312; rules E, F, I, UP, B (`backend/pyproject.toml`)
- Layering: API → services → repositories; provider logic in `integrations/` and `channels/`
- Pydantic schemas in `schemas/`; enums and models in `domain/`
- Async pytest with `pytest-asyncio`

### Frontend

- TypeScript strict via project references (`tsconfig.json`, `tsconfig.app.json`)
- Functional React components; colocate tests as `*.test.tsx` / `*.test.ts`
- API calls through `apiClient` with `credentials: 'include'` and CSRF header on mutating requests
- UI preferences (theme, sidebar collapse, selected shop) may use `localStorage`; auth tokens must not
- Tailwind v4 via `@tailwindcss/vite`

### General

- Minimize diff scope; match existing naming and patterns in surrounding code
- Channel credentials are encrypted at rest; never returned in API responses or logs
- Redact secrets in failed-job payloads and error surfaces
- Provider access tokens are shop-specific channel credentials encrypted with `TOKEN_ENCRYPTION_KEY`
- Global Meta credentials (`META_APP_ID`, `META_APP_SECRET`) validate signatures; they are not shop page tokens

## Security rules

These rules are non-negotiable.

| Rule | Why |
|------|-----|
| **Never commit secrets** | `.env` is gitignored; use `.env.example`. Frontend env may contain browser-safe URLs (`VITE_*`) only. Channel secrets belong in encrypted per-shop channel account records, not in `.env`. |
| **Never store JWTs in `localStorage`** | Auth uses HttpOnly cookies set by `backend/app/api/v1/auth.py`. `frontend/src/services/tokenStorage.ts` is a compatibility shim that intentionally never persists tokens. `apiClient` uses `credentials: 'include'`. |
| **Never bypass webhook signature checks in production** | `WEBHOOK_SIGNATURE_BYPASS` is rejected in staging/production (`backend/app/core/config.py`). Tests set bypass only in `conftest.py`. Production must keep `WEBHOOK_SIGNATURE_BYPASS=false`. |
| **Preserve audit logs** | `AdminAuditLog` and `AgentDecisionAudit` are immutable trails. Use `AuditService` / `OrderAuditService`. Do not delete, skip, or weaken audit writes for convenience. |
| **Preserve idempotency** | Webhook events, channel messages (`idempotency_key` unique constraint), and outbound message dedup must remain intact. Do not weaken unique constraints or skip idempotency checks. |

Production must also set a strong `TOKEN_ENCRYPTION_KEY`, restrict `CORS_ORIGINS`, and avoid frontend provider-token variables.

## PR rules for agents

1. **Keep changes small** — focused diffs; no unrelated refactors.
2. **Include tests for behavior changes** — backend pytest; frontend vitest.
3. **Run targeted checks before finishing:**
   - Backend: `pytest` on affected modules; migrations if schema changed
   - Frontend: `npm run typecheck` + `npm test` on touched areas
4. **Cite changed files and test output** in the final response — list modified paths and paste relevant pytest / typecheck / vitest output.
5. **Do not commit unless explicitly asked** by the user.

## Admin hub routes (reference)

- `/` Overview
- `/inbox`, `/inbox/:id`, `/inbox/:id/intelligence`
- `/catalog/products`, `/catalog/attributes`, `/catalog/resolver`, `/catalog/mapping`
- `/orders`
- `/automation/*`
- `/ai/*`
- `/handoffs`
- `/analytics`
- `/system/*`
