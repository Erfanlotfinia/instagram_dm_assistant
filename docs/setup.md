# Setup Guide

This guide covers local development setup for the Multi-channel Catalog Commerce Assistant v1.0.0.

## Prerequisites

- Docker Desktop (recommended) or local PostgreSQL 16, Redis 7, RabbitMQ 3, and Qdrant 1.12+
- Node.js 20+ for frontend development outside Docker
- Python 3.12+ for backend development outside Docker

## Quick start (Docker Compose)

```bash
cp .env.example .env
docker compose up --build
```

Services:

| Service | URL |
| --- | --- |
| Backend API | http://localhost:8800 |
| Frontend admin | http://localhost:5173 |
| RabbitMQ management | http://localhost:15672 |
| Qdrant | http://localhost:6333 |

Health checks:

```bash
curl http://localhost:8800/health
curl http://localhost:8800/ready
```

## Local backend (without Docker)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
export DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/modira
export REDIS_URL=redis://localhost:6379/0
export RABBITMQ_URL=amqp://guest:guest@localhost:5672/
export QDRANT_URL=http://localhost:6333
alembic upgrade head
pytest app/tests -q
uvicorn app.main:app --reload --port 8000
```

## Local frontend (without Docker)

```bash
cd frontend
npm ci
npm run typecheck
npm test
npm run dev
```

Set `VITE_API_BASE_URL=http://localhost:8800` (or your backend URL).

## Seed data

```bash
docker compose exec backend python -m app.scripts.seed
docker compose exec backend python -m app.scripts.seed_demo_data
```

## Related docs

- [Documentation index](README.md)
- [UI design guide](ui-design-guide.md)
- [Production deployment](production-deployment.md)
- [Security configuration](security_configuration.md)
- [Migration guide](migration-guide.md)
- [Troubleshooting](troubleshooting.md)
- [Operator guide](operator-guide.md)
