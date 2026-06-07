# Instagram DM Assistant

Sprint 0 establishes the production-ready foundation for an advanced Instagram DM ordering agent. This repository intentionally contains only infrastructure, application skeletons, health checks, and testing scaffolding. Instagram, ordering, and LLM workflows will be implemented in later sprints.

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

- `backend`: FastAPI API server on <http://localhost:8000>
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

- `DATABASE_URL`
- `REDIS_URL`
- `RABBITMQ_URL`
- `QDRANT_URL`
- `OPENAI_API_KEY`
- `APP_ENV`
- `LOG_LEVEL`
- `JWT_SECRET_KEY`

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
docker compose down
docker compose down -v
```

Health endpoints:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/health
```

## Backend development

From the `backend/` directory:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
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
```

## Database migrations

Alembic is configured under `backend/app/db/migrations` and uses `DATABASE_URL` from the environment.

Apply migrations inside the backend container:

```bash
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

Run frontend tests:

```bash
cd frontend
npm test
```

Build the frontend:

```bash
cd frontend
npm run build
```

## Implementation notes

- API routers remain thin and expose only HTTP boundaries.
- Cross-cutting concerns live in `backend/app/core`.
- Structured JSON logging is configured at application startup for container-friendly log ingestion.
- Global exception handlers normalize API error responses.
- CORS allows the local Vite frontend origin by default.
- OpenAI, Instagram, order management, and agent logic are intentionally represented only by environment placeholders and empty extension directories.
