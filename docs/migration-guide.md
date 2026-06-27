# Migration Guide

## Local Docker

Migrations run automatically via the one-shot `backend-migrate` service before the backend starts:

```bash
docker compose up -d
```

To run migrations manually:

```bash
docker compose run --rm backend-migrate
# or
docker compose exec backend alembic upgrade head
```

Production uses the same `backend-migrate` pattern; see [production-deployment.md](production-deployment.md).

## Local shell

Use a database URL that resolves from your shell rather than the Compose hostname:

```bash
cd backend
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/modira alembic upgrade head
```

## Validation checklist

1. Run `alembic heads` and confirm a single head.
2. Run `alembic upgrade head` against a clean PostgreSQL database.
3. Run backend tests that cover migrations and order/payment transitions.
4. Never run production migrations without a database backup and rollback plan.
