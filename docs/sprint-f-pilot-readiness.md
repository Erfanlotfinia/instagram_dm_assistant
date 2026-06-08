# Sprint F: Pilot readiness guide

Sprint F prepares the Instagram Fashion Order Agent for real pilot usage with stronger analytics, reliability, health checks, failed job visibility, idempotency, security, and documentation.

## Analytics dashboard

Shop-scoped analytics endpoints (all support `date_from` / `date_to`):

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/shops/{shop_id}/analytics/funnel` | Conversion funnel metrics |
| `GET /api/v1/shops/{shop_id}/analytics/lost-demand` | Paginated lost demand with product, reason, revenue |
| `GET /api/v1/shops/{shop_id}/analytics/operator-performance` | Operator assignment, resolution, revenue |
| `GET /api/v1/shops/{shop_id}/analytics/agent-performance` | Auto-send, preview, handoff, LLM quality |

Admin UI: `/analytics` — funnel cards, post revenue, lost demand, agent/operator tables, date filters.

## System health

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Simple liveness |
| `GET /ready` | Dependency checks: postgres, redis, rabbitmq, qdrant, openai_config |

Admin UI: `/system-health` — readiness cards, failed jobs list, retry/ignore actions.

## Failed jobs

RabbitMQ uses primary, retry (TTL), and DLQ queues. Exhausted jobs are stored in `failed_jobs` with shop isolation.

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/shops/{shop_id}/failed-jobs` | List failed jobs |
| `POST /api/v1/shops/{shop_id}/failed-jobs/{id}/retry` | Requeue job (admin+) |
| `POST /api/v1/shops/{shop_id}/failed-jobs/{id}/ignore` | Mark ignored (admin+) |

## Idempotency guarantees

- Instagram webhook message IDs are unique (`messages.instagram_message_id`)
- Agent runs are unique per inbound message (`agent_runs.input_message_id`)
- Order confirmation skips duplicate inventory reservation
- Payment callbacks ignore duplicate paid status / provider reference
- Inventory movements deduplicated by order reference

## Security and audit

Sensitive actions are logged to `admin_audit_logs`, including:

- Agent setting changes
- Product mapping create/update
- Inventory reserve/release
- Order status and manual payment
- Message approval/edit/reject
- Handoff take/release
- Failed job retry/ignore

## Production readiness checklist

- [ ] `GET /ready` returns `ok` for all dependencies
- [ ] `OPENAI_API_KEY`, `JWT_SECRET_KEY`, and `TOKEN_ENCRYPTION_KEY` set for production
- [ ] CORS restricted via `CORS_ORIGINS`
- [ ] Meta webhook verify token and optional signature validation configured
- [ ] Demo shop seeded and onboarding checklist completed
- [ ] Analytics dashboard reviewed for pilot shop
- [ ] Failed jobs page monitored during rollout
- [ ] Worker and scheduler services running

## Run Sprint F tests

```bash
cd backend && pytest app/tests/test_sprint_f.py -q
cd frontend && npm test -- SystemHealthPage AnalyticsPage
```
