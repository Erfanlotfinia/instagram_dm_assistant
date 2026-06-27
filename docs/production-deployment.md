# Production Deployment (Docker Compose)

This guide covers running Modira with the production Docker Compose overlay. Local development continues to use `docker-compose.yml` alone (Vite dev servers, bind mounts, automatic migrations via `backend-migrate`, and optional admin bootstrap).

## Files

| File | Purpose |
| --- | --- |
| `docker-compose.yml` | Base stack shared by local and production |
| `docker-compose.prod.yml` | Production overlay — no bind mounts, Nginx static assets, split migrations |
| `.env.production.example` | Production env template (placeholders only) |

## Prerequisites

- Docker Engine 24+ and Docker Compose v2.24+ (`!reset` merge support)
- TLS-terminated reverse proxy in front of public services (recommended)
- Strong secrets for JWT, token encryption, database, and RabbitMQ

## Configure environment

```bash
cp .env.production.example .env
# Edit .env — replace every placeholder; never commit the populated file
```

Required production settings:

- `APP_ENV=production`
- HTTPS values for `PUBLIC_API_BASE_URL`, `FRONTEND_BASE_URL`, `CORS_ORIGINS`, and `VITE_*` build args
- Strong non-default `JWT_SECRET_KEY` and `TOKEN_ENCRYPTION_KEY` (min 32 characters)
- `WEBHOOK_SIGNATURE_BYPASS=false`
- Meta credentials when Instagram/WhatsApp providers are enabled

## Validate and start

Inspect the merged configuration:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml config
```

Build and start the production stack:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Production differences from local:

| Concern | Local (`docker-compose.yml`) | Production (with overlay) |
| --- | --- | --- |
| Source bind mounts | Yes (`./backend/app`, `./frontend`, etc.) | No — image contents only |
| Migrations | One-shot `backend-migrate` service | Same one-shot service, no bind mounts |
| Backend startup | Optional `ensure_admin` + Uvicorn | Uvicorn only (`ENABLE_ENSURE_ADMIN=false` by default) |
| Frontend / landing | Vite dev servers on 5173 / 5174 | Nginx serving built assets on 8080 / 8081 |
| Backend user | Non-root (`uid 1000`) | Non-root (`uid 1000`) |

## Service startup order

1. Infrastructure: `postgres`, `redis`, `rabbitmq`, `qdrant`
2. `backend-migrate`: runs `alembic upgrade head` once and exits
3. `backend`: Uvicorn API (waits for successful migration)
4. `worker`, `scheduler`: start after backend is healthy
5. `frontend`, `landing`: Nginx serving pre-built static files

## First admin user

Production does **not** create a bootstrap admin by default. Choose one:

1. **One-time bootstrap** (first deploy only): set `ENABLE_ENSURE_ADMIN=true` in `.env`, start the stack, sign in, then set `ENABLE_ENSURE_ADMIN=false` and redeploy.
2. **Manual provisioning**: create an admin through your identity process or run `docker compose exec backend python -m app.scripts.ensure_admin` once with explicit credentials in `.env`.

## Manual migrations

Migrations run automatically via `backend-migrate` on each deploy. To run manually:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm backend-migrate
```

Or from a running backend container:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec backend alembic upgrade head
```

Always take a Postgres backup before applying migrations in production. See [Migration guide](migration-guide.md).

## Health checks

```bash
curl -fsS http://localhost:${BACKEND_HOST_PORT:-8000}/health
curl -fsS http://localhost:${BACKEND_HOST_PORT:-8000}/ready
curl -fsS http://localhost:${FRONTEND_HOST_PORT:-8080}/health
curl -fsS http://localhost:${LANDING_HOST_PORT:-8081}/health
```

Verify the backend runs as non-root:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec backend id -u
# Expected: 1000 (not 0)
```

## Production smoke test

```bash
bash scripts/docker_prod_smoke_test.sh
```

This script generates temporary production-grade secrets, validates the merged compose config, builds images, starts the stack, checks health endpoints, confirms the backend is non-root, and tears down.

## Backup and restore

Back up before schema migrations, major upgrades, or incident response. Test restores in a non-production environment.

### PostgreSQL

**Backup** (logical dump while stack is running):

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T postgres \
  pg_dump -U postgres -Fc "${POSTGRES_DB}" > "modira-postgres-$(date +%Y%m%d-%H%M%S).dump"
```

**Restore** (into a fresh or emptied database — destructive):

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T postgres \
  pg_restore -U postgres -d "${POSTGRES_DB}" --clean --if-exists < modira-postgres-YYYYMMDD-HHMMSS.dump
```

Volume-level backup (stop writes first):

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml stop backend worker scheduler backend-migrate
docker run --rm -v modira_postgres_data:/data -v "$PWD:/backup" alpine \
  tar czf /backup/postgres-data-$(date +%Y%m%d).tar.gz -C /data .
docker compose -f docker-compose.yml -f docker-compose.prod.yml start backend worker scheduler
```

Replace `modira_postgres_data` with the actual volume name from `docker volume ls`.

### Redis

Redis holds ephemeral state (locks, rate limits, session-adjacent caches). Back up if you rely on persisted keys beyond TTL.

**Backup** (RDB snapshot via `SAVE` or copy AOF/data dir):

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec redis redis-cli BGSAVE
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec redis \
  sh -c 'cat /data/dump.rdb' > "modira-redis-$(date +%Y%m%d).rdb"
```

**Restore** (stop Redis, replace RDB, restart):

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml stop redis
docker run --rm -v modira_redis_data:/data -v "$PWD:/backup" alpine \
  sh -c 'cp /backup/modira-redis-YYYYMMDD.rdb /data/dump.rdb && chown 999:999 /data/dump.rdb'
docker compose -f docker-compose.yml -f docker-compose.prod.yml start redis
```

### RabbitMQ

**Backup** (definitions + messages require management plugin export or volume snapshot):

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec rabbitmq \
  rabbitmqctl export_definitions /tmp/definitions.json
docker compose -f docker-compose.yml -f docker-compose.prod.yml cp \
  rabbitmq:/tmp/definitions.json "modira-rabbitmq-definitions-$(date +%Y%m%d).json"
```

For full message durability, snapshot the `rabbitmq_data` volume while RabbitMQ is stopped.

**Restore definitions**:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml cp \
  modira-rabbitmq-definitions-YYYYMMDD.json rabbitmq:/tmp/definitions.json
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec rabbitmq \
  rabbitmqctl import_definitions /tmp/definitions.json
```

### Qdrant

Qdrant stores vector embeddings for catalog search. Re-indexing from Postgres is possible but slow; prefer volume backups.

**Backup** (volume snapshot — stop Qdrant for consistency):

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml stop qdrant backend worker scheduler
docker run --rm -v modira_qdrant_data:/data -v "$PWD:/backup" alpine \
  tar czf /backup/qdrant-data-$(date +%Y%m%d).tar.gz -C /data .
docker compose -f docker-compose.yml -f docker-compose.prod.yml start qdrant backend worker scheduler
```

**Restore**:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml stop qdrant
docker run --rm -v modira_qdrant_data:/data -v "$PWD:/backup" alpine \
  sh -c 'rm -rf /data/* && tar xzf /backup/qdrant-data-YYYYMMDD.tar.gz -C /data'
docker compose -f docker-compose.yml -f docker-compose.prod.yml start qdrant
```

After a Qdrant restore, verify search quality and consider a catalog re-index if embeddings drifted.

## Related docs

- [Migration guide](migration-guide.md)
- [Security configuration](security_configuration.md)
- [Troubleshooting](troubleshooting.md)
- [Production infrastructure (Kubernetes)](production_infrastructure.md)
