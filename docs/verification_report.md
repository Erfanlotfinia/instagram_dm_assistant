# Audit Remediation Verification Report

Last verified: 2026-06-13

## Summary

| Gate | Result |
|------|--------|
| Backend pytest (`app/tests`) | **389 passed** |
| Backend ruff | pass (prior) |
| Alembic `upgrade head` (clean DB) | CI / `scripts/check_migrations.sh`; local Docker Postgres required |
| Frontend typecheck | pass |
| Frontend Vitest | **51 passed** |
| Frontend lint | pass |
| Frontend build | pass |
| Docker Compose smoke | CI job `docker-smoke`; local: `scripts/docker_smoke_test.ps1` |
| `docker compose config` | pass |
| Scenario regression runner | real `ScenarioRegressionRunner` (150 scenarios); safety counts = 0 |

## Social admin integration (2026-06-13)

- `SocialAdminOrchestrator` runs automation-first before legacy LLM extraction for new conversations without active Instagram product flow.
- `ConversationContextService` supports DB persistence via `conversation_context_items` tables.
- `ScenarioRegressionRunner` replaces hardcoded API metrics.
- CLI: `python -m app.scripts.run_scenario_regression` (requires DATABASE_URL).

See [FINAL_READINESS_REPORT.md](FINAL_READINESS_REPORT.md) for full QA report.

## Phase 1 — backend test collection/runtime

- **326 tests** collect and pass (`py -3.12 -m pytest app/tests -q`, no `-x`).
- **Per-file pass**: all 60 `test_*.py` modules run individually without failures.
- **`create_text_message`**: single implementation in `fixtures/agent.py`; `fixtures/orders.py` re-exports for order-flow tests.
- **`pytest.mark.integration`**: registered in `pyproject.toml` (removes collection warning for `test_migrations.py`).
- **`test_order_agent_flow`**: `test_agent_flow_creates_draft_and_payment_link` passes with `seed_draft_order`, complete slots, and controlled autopilot.

## Remediation areas covered

- **Test infrastructure**: savepoint-isolated `db_session`, test env (`LLM_MODE=mock`, `WEBHOOK_SIGNATURE_BYPASS`), Redis idempotency cleanup, request-context reset between tests.
- **Failed jobs security**: admin-only APIs, redacted payloads, audit on retry/ignore, legacy endpoint removed.
- **Production config**: staging/production secret and CORS validation; webhook signature required outside development.
- **Outbox webhooks**: transactional outbox for reliable publish after DB commit.
- **Order/payment invariants**: customer confirmation before payment link; reservation required for mark-paid.
- **Variant archive**: soft-delete API; archived variants excluded from resolver.
- **TRL validation**: `deterministic_regression` vs `live_llm_staging` modes with honest metric labels.
- **Agent orchestrator**: per-message trace IDs; `confirm_order` payment path uses existing active order; returns `false` on invalid LLM JSON.

## Local verification commands

```bash
bash scripts/verify_local.sh
bash scripts/docker_smoke_test.sh   # requires Docker
```

## CI

GitHub Actions workflow `.github/workflows/ci.yml`:

- `backend`: ruff, migrations, pytest, resolver benchmark, golden replay
- `frontend`: typecheck, lint, test, build
- `docker-smoke`: compose config, build, health/ready checks

## Operational references

- [security_configuration.md](security_configuration.md)
- [production_incident_response.md](production_incident_response.md)
- [migration_guide.md](migration_guide.md)
- [failed-jobs-runbook.md](failed-jobs-runbook.md)
- [analytics-guide.md](analytics-guide.md)

## Remaining risks

- Docker smoke depends on host resources and first-time image build time.
- Live LLM / Meta Graph integrations are mocked in tests; staging validation still requires real credentials.
- JWT test secret is below 32 bytes (warning only in tests).
