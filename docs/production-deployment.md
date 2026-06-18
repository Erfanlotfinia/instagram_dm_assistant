# Production Deployment Guide

## Prerequisites

- Docker host or Kubernetes cluster with PostgreSQL, Redis, RabbitMQ, and Qdrant (managed or self-hosted)
- Meta Developer app with Instagram messaging permissions
- OpenAI API key for agent extraction and semantic search
- TLS termination (reverse proxy or load balancer)

## Recommended topology

```text
Internet → TLS proxy → backend API (FastAPI)
                    → frontend static build (CDN or nginx)
                    → worker (RabbitMQ consumer)
                    → scheduler (background jobs)
Postgres / Redis / RabbitMQ / Qdrant (private network)
```

## Steps

1. Copy `.env.example` to `.env` and set production values:
   - `APP_ENV=production`
   - Strong `JWT_SECRET_KEY` and `TOKEN_ENCRYPTION_KEY`
   - `CORS_ORIGINS` limited to your admin domain
   - `META_APP_SECRET` for webhook signature verification
   - Real `OPENAI_API_KEY`

2. Run database migrations:
   ```bash
   docker compose exec backend alembic upgrade head
   ```

3. Seed a pilot shop (optional):
   ```bash
   docker compose exec backend python -m app.scripts.seed
   ```

4. Start services:
   ```bash
   docker compose up -d backend worker scheduler frontend
   ```

5. Verify readiness:
   ```bash
   curl https://api.example.com/api/v1/ready
   curl https://api.example.com/api/v1/metrics
   ```

6. Configure Meta webhook callback URL to `https://api.example.com/api/v1/webhooks/instagram`.

## Production checklist

- [ ] Secrets stored in a vault, not in git
- [ ] `ENABLE_REAL_PROVIDER_SEND=true` only when Graph API tokens are valid
- [ ] Rate limiting enabled (`RATE_LIMIT_ENABLED=true`)
- [ ] Log aggregation configured (JSON stdout → Loki/Datadog/CloudWatch)
- [ ] Prometheus scraping `/api/v1/metrics`
- [ ] Backups for Postgres
- [ ] DLQ monitored for poison messages

## Production safety validation

The API validates production settings at startup. When `APP_ENV=production`, deployment must provide:

- a non-default `JWT_SECRET_KEY` with at least 32 characters;
- a non-default `TOKEN_ENCRYPTION_KEY` with at least 32 characters;
- `META_APP_SECRET` so Meta webhook signatures are verified;
- explicit HTTPS `CORS_ORIGINS` with no wildcard.

Deployments that do not meet these requirements fail fast instead of accepting unsafe traffic.
