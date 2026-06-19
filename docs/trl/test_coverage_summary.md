# Test Coverage Summary — TRL Evidence Pack

**Assessment date:** 2026-06-09  
**Method:** Static analysis of test files in repository (test execution not run in authoring environment)

---

## Overview

| Suite | Files | Approx. tests | Framework |
|-------|------:|--------------:|-----------|
| Backend | 45 | ~190 | pytest |
| Frontend | 21 | ~33 | vitest + Testing Library |
| E2E (backend integration) | 1 | 8 | pytest (in-process, test DB) |
| Browser E2E | 0 | 0 | — |
| Manual / checklist | 3 docs | — | Human QA |

---

## Backend tests

### By capability area

| Area | Test file(s) | Tests | Covers |
|------|--------------|------:|--------|
| **Webhook ingestion** | `test_webhook_ingestion.py`, `test_webhook_api.py` | 10 | Payload parsing, idempotency, API contract |
| **Message worker** | `test_message_consumer.py` | 2 | Consumer ack/nack, job handling |
| **Redis lock** | `test_redis_lock.py` | 2 | Lock acquire/release |
| **LLM extraction** | `test_llm_extraction_service.py` | 2 | JSON extraction, validation |
| **Agent safety** | `test_agent_safety_controls.py` | 6 | Invalid JSON fallback, risk scoring, handoff triggers |
| **Normalization** | `test_sprint_a_normalization_unit.py` | 3 | Color/size aliases |
| **Variant / inventory** | `test_variants_api.py`, `test_inventory_service.py` | 11 | Resolver API, reserve/release |
| **Order flow** | `test_order_agent_flow.py`, `test_order_service.py`, `test_orders_api.py` | 11 | Draft, confirm, payment, cancel |
| **State machine** | `test_state_machine_service.py` | 4 | Workflow transitions |
| **Orchestrator** | `test_conversation_orchestrator.py` | 2 | Multi-step processing |
| **E2E order journey** | `test_sprint7_e2e.py` | 8 | Webhook → orchestrator → paid order, failures |
| **Handoff** | `test_handoff_service.py` | 3 | Take-over, release, flags |
| **Simulator** | `test_sprint_e_simulator.py` | 4 | DM simulator API |
| **TRL validation** | `test_trl_validation.py` | 7 | Runner, seed, isolation, reset |
| **Pilot readiness** | `test_pilot_readiness.py` | 7 | Settings, emergency stop, limits, readiness API |
| **Analytics / ops** | `test_analytics_api.py`, `test_sprint_f.py`, `test_health.py` | 14 | Funnel, failed jobs, readiness |
| **Security** | `test_sprint7_security.py`, `test_auth_api.py`, `test_roles.py` | 8 | Auth, roles, audit |
| **Product mapping** | `test_instagram_product_maps_api.py`, `test_fashion_competitive_mvp.py` | 14 | Maps, competitive MVP flows |
| **Conversations / admin API** | `test_conversations_api.py`, `test_dashboard_api.py` | 6 | Inbox, dashboard |
| **Other** | migrations, config, semantic search, sprints B/C/D/E | ~40 | Feature sprints |

### TRL-relevant backend commands

```bash
cd backend
pytest app/tests/test_trl_validation.py -v
pytest app/tests/test_pilot_readiness.py -v
pytest app/tests/test_sprint7_e2e.py -v
pytest app/tests/test_order_agent_flow.py -v
pytest app/tests/test_agent_safety_controls.py -v
pytest  # full suite
```

---

## Frontend tests

| Page / component | Test file | Tests | Covers |
|------------------|-----------|------:|--------|
| TRL Validation | `TRLValidationPage.test.tsx` | 4 | Run list, metrics display, actions |
| Pilot Readiness | `PilotReadinessPage.test.tsx` | 2 | Readiness UI, emergency stop |
| DM Simulator | `DMSimulatorPage.test.tsx` | 2 | Simulator page render/actions |
| System Health | `SystemHealthPage.test.tsx` | 3 | Health cards, failed jobs |
| Conversations | `ConversationsPage.test.tsx`, `ConversationDetailPage.test.tsx` | 6 | Inbox, detail |
| Analytics | `AnalyticsPage.test.tsx`, `PostRevenueAnalyticsPage.test.tsx` | 2 | Analytics views |
| Agent Studio | `AgentStudioSettingsPage.test.tsx` | 1 | Settings |
| Orders | `OrdersPage.test.tsx`, `OrderDetailPage.test.tsx` | 2 | Order management |
| Other | Dashboard, Login, Onboarding, Risk, Recovery, Upsell, App shell | ~11 | Shell and ancillary pages |

### Frontend commands

```bash
cd frontend
npm test
npm test -- TRLValidationPage PilotReadinessPage DMSimulatorPage SystemHealthPage
npm run typecheck
npm run build
```

---

## E2E / manual tests

### Automated backend E2E (`test_sprint7_e2e.py`)

- Inbound webhook → paid order (Persian variant message)
- Duplicate webhook idempotency
- Payment callback idempotency
- Order confirmation idempotency
- Failed payment handling
- Worker failure scenarios (partial)

**Limitation:** Runs against test database with mocked/no-op publisher; not full Docker Compose stack.

### Manual checklists (in repository)

| Document | Purpose |
|----------|---------|
| README — Sprint 6 manual QA | Admin workflows across auth, dashboard, conversations, products, orders, settings |
| `docs/pilot_test_script.md` | TRL 6 pilot scenarios, rollback, daily review |
| `docs/demo-scenario.md` | Persian commerce message demo flow |

### Missing E2E

- No Playwright/Cypress suite
- No TRL validation UI → full backend run browser test
- No load/stress test scripts

---

## Missing tests (gaps)

| Gap | Risk | Priority |
|-----|------|----------|
| Browser E2E for operator inbox, handoff, TRL dashboard | High — UX regressions undetected | P1 |
| PostgreSQL concurrent inventory reservation | High — oversell in pilot | P1 |
| RabbitMQ retry delay + DLQ integration | High — message loss/duplicate processing | P1 |
| Live OpenAI extraction golden corpus | High — TRL 5 AI claim unsupported | P1 |
| Webhook burst / rate limit | Medium | P2 |
| TRL runner stubbed metrics (payment, security, idempotency) | Medium — false TRL pass | P1 |
| Pilot readiness `status==passed` vs `completed` | Medium — false pilot block/pass | P1 |
| Multi-operator concurrent handoff | Medium | P2 |
| Real payment provider callbacks | Medium (TRL 6+) | P2 |
| Analytics golden fixture at scale | Low | P3 |

---

## High-risk areas (test debt)

1. **LLM extraction quality** — only 2 direct unit tests; TRL runner bypasses OpenAI
2. **Queue + worker reliability** — limited integration coverage; retry queue behavior questioned in prior assessment
3. **Inventory concurrency** — unit tests only; no parallel reservation stress test
4. **Payment security** — mock provider; callback signature not production-grade
5. **Cross-shop isolation** — partial; no full endpoint matrix
6. **Pilot automation gates** — tested in unit tests but not in live pilot execution logs

---

## Recommended test additions for TRL 5/6

1. CI job: `pytest` + export TRL report on `trl-commerce-demo` seed (subset or full 100 scenarios)
2. Compose integration test: webhook POST → worker consumes → conversation state updated
3. Labeled LLM eval script (50–100 Persian/English DMs) with minimum F1 thresholds
4. Playwright: login → TRL validation run → view failed scenarios → pilot readiness check
5. PostgreSQL `pytest` marker for inventory concurrency (2+ parallel confirmations)
