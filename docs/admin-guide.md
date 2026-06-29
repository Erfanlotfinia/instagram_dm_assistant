# Admin Guide

Configuration and security responsibilities for shop admins. Screen map: [ui-design-guide.md](./ui-design-guide.md).

## Shop setup checklist

| Step | UI location |
|------|-------------|
| Create shop, invite members | **System → Shops** |
| Currency, language, agent defaults | **System → Settings** |
| Connect channels | **System → Channels** (Instagram OAuth, Telegram bot) |
| Import / create catalog | **Catalog → Products**; optional `/api/v1/catalog/import` |
| Map Instagram posts | **Catalog → Mapping** |
| Set risk thresholds | **Automation → Risk** |
| Pilot readiness | **System → Rollout → Readiness** |

## Agent & risk settings

| Setting | Location | Effect |
|---------|----------|--------|
| Auto reply | Settings / agent studio | Enable automation |
| Intent / slot confidence | Automation → Risk | Handoff when below threshold |
| High-value preview | Risk settings | Require operator approval |
| Handoff mode | Agent settings | Escalation policy |
| Default language | Shop settings | `fa` recommended for Iranian pilots |

## Catalog management

- Products and variants with accurate stock (**Catalog → Products**).
- Attribute dictionary for normalization (**Catalog → Attributes**).
- Resolver test bench before go-live (**Catalog → Resolver**).
- Reindex after bulk import: `POST /api/v1/catalog/reindex`.

## Monitoring

| Signal | Where |
|--------|-------|
| Dependency health | **System → Health** (`/api/v1/ready`) |
| Failed workers | **System → Failed Jobs** (sidebar badge) |
| Prometheus | `/api/v1/metrics` (ops; not in UI) |
| Pilot metrics | **System → Rollout → Pilot Control** |

Key metrics: inbound/processed messages by provider, handoffs, orders created/paid, queue DLQ depth.

## Security (admin responsibilities)

- Rotate `JWT_SECRET_KEY` and `TOKEN_ENCRYPTION_KEY` on compromise.
- Keep `META_APP_SECRET` and channel tokens confidential (encrypted at rest; never in API responses).
- Production: `WEBHOOK_SIGNATURE_BYPASS=false`, strict `CORS_ORIGINS`.
- Review audit logs for login and admin actions.

Details: [security_configuration.md](./security_configuration.md).

## Pilot & incidents

- **Emergency stop:** Rollout → Pilot Control halts automated outbound.
- **Incidents:** Rollout → Incidents or `/incidents`.
- **TRL validation:** Rollout → TRL Validation before expanding scope.

See [pilot_test_script.md](./pilot_test_script.md) and [trl/pilot_plan.md](./trl/pilot_plan.md).
