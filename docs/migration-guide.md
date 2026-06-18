# Migration Guide

## Local Docker

```bash
docker compose exec backend alembic upgrade head
```

The backend container also runs `alembic upgrade head` before Uvicorn starts.

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
