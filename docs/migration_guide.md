# Migration Guide

Alembic migrations live in `backend/app/db/migrations/versions/`.

## Local upgrade

```bash
cd backend
alembic upgrade head
```

## Docker Postgres

```bash
docker compose up -d postgres
cd backend
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/modira alembic upgrade head
```

## Create migration

```bash
cd backend
alembic revision -m "describe_change"
```

## Rollback

```bash
cd backend
alembic downgrade -1
```

## Clean DB validation

```bash
cd backend
bash scripts/check_migrations.sh
```

CI runs `alembic upgrade head` against a clean PostgreSQL service before pytest.
