# Modira Documentation Index

Start here when onboarding or redesigning the product.

## For UI / product design

| Document | Use when |
|----------|----------|
| **[ui-design-guide.md](./ui-design-guide.md)** | Redesigning admin screens, IA, states, flows |
| [operator-guide.md](./operator-guide.md) | Operator daily workflows |
| [admin-guide.md](./admin-guide.md) | Shop setup, agent config, security |
| [analytics-guide.md](./analytics-guide.md) | Dashboard metrics meaning |

## For API & integration

| Document | Use when |
|----------|----------|
| **[api-documentation.md](./api-documentation.md)** | Full REST API reference |
| [api.md](./api.md) | Quick link to OpenAPI + API guide |
| [environment-variables.md](./environment-variables.md) | Config reference |

## For local dev & ops

| Document | Use when |
|----------|----------|
| [setup.md](./setup.md) | First-time local stack |
| [migration-guide.md](./migration-guide.md) | Alembic migrations |
| [production-deployment.md](./production-deployment.md) | Docker Compose production |
| [troubleshooting.md](./troubleshooting.md) | Common failures |
| [failed-jobs-runbook.md](./failed-jobs-runbook.md) | DLQ retry/ignore |
| [security_configuration.md](./security_configuration.md) | Production security |

## Architecture

| Document | Use when |
|----------|----------|
| [order-correctness-architecture.md](./order-correctness-architecture.md) | Order state machine |
| [catalog-intelligence-architecture.md](./catalog-intelligence-architecture.md) | Import, Qdrant, resolver |
| [channels-guide.md](./channels-guide.md) | Webhook → worker flow, provider matrix, onboarding |
| [scenarios/social_admin_automation.md](./scenarios/social_admin_automation.md) | Scenario router & handlers |

## Channels

| Document | Use when |
|----------|----------|
| **[channels-guide.md](./channels-guide.md)** | Architecture, security, onboarding, provider matrix |
| [meta-webhook-setup.md](./meta-webhook-setup.md) | Meta/Instagram webhook setup |

## Catalog

| Document | Use when |
|----------|----------|
| **[catalog-guide.md](./catalog-guide.md)** | Data model, presets, import, resolver, quality checks |
| [catalog-intelligence-architecture.md](./catalog-intelligence-architecture.md) | Qdrant, hybrid search, traces, benchmarks |

## Pilot & validation

| Document |
|----------|
| [pilot_test_script.md](./pilot_test_script.md) |
| [trl/pilot_plan.md](./trl/pilot_plan.md) |
| [trl/operational_readiness_checklist.md](./trl/operational_readiness_checklist.md) |
| [simulator-guide.md](./simulator-guide.md) |

## Release

| Document |
|----------|
| [release/v1.0.0.md](./release/v1.0.0.md) |

## Repository guides

| Document |
|----------|
| [../AGENTS.md](../AGENTS.md) — engineering conventions for agents |
| [../landing/README.md](../landing/README.md) — marketing site |

## Brand assets

Design tokens and logos live in [`../brand/`](../brand/README.md). Admin app imports `brand/04_brand_tokens/modira-brand-tokens.css`.

---

**Removed / consolidated (2026-06):** duplicate stubs (`analytics_guide.md`, `simulator_guide.md`, `migration_guide.md`, scenario module stubs, sprint notes, point-in-time QA reports) were merged into the guides above or deleted as deprecated. The `docs/channels/` directory was consolidated into [channels-guide.md](./channels-guide.md). The `docs/catalog/` directory was consolidated into [catalog-guide.md](./catalog-guide.md).
