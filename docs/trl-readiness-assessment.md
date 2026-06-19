# TRL Readiness Assessment — AI Social Media Admin OS

Date assessed: 2026-06-08

## A. Current estimated TRL

**Current overall estimate: TRL 4+ (lab-validated integrated prototype), not yet TRL 5.**

The repository contains integrated FastAPI, PostgreSQL/Alembic, RabbitMQ worker, Redis lock, Qdrant/OpenAI adapters, React admin, Docker Compose, backend pytest coverage, and frontend component tests. The product has most key components wired together in a lab environment, including webhook ingestion, message persistence, order orchestration, mock payments, admin inbox, simulator, handoff, audit traces, analytics, and failed-job management.

It is **not yet above TRL 4** because the evidence is mostly unit/API/component tests and local/demo docs. There is not yet a reproducible relevant-environment validation pack with realistic Instagram payloads, realistic catalog data, real/mocked-at-boundary OpenAI and Qdrant runs, end-to-end Docker Compose worker evidence, load/reliability measurements, operational SLOs, or pilot runbooks proving performance and failure handling under realistic conditions.

## B. Component-by-component TRL assessment

| # | Component | Current maturity | Est. TRL | What exists | Missing requirements | Technical risks | Evidence needed | Tests needed | Recommended fixes |
|---:|---|---|---:|---|---|---|---|---|---|
| 1 | Instagram webhook ingestion | lab-only | 4 | Webhook verification, optional Meta signature check, inbound JSON parsing, event persistence, account lookup, customer/conversation/message creation, idempotency by Instagram message id, queue publish. | Evidence with current Meta Graph webhook fixtures, multiple event types, malformed/retry behavior, signature-negative tests in a deployed-like stack. | Unknown account messages are ignored after webhook event creation; no proof of Meta retry semantics; payload parser scope may miss comments/story replies/ad comments needed for multi-channel shops. | Meta webhook fixture suite, signature validation report, docker-compose run proving webhook -> DB -> queue. | Contract tests using current Meta payloads, duplicate delivery tests, unknown-recipient observability tests, webhook burst/rate-limit tests. | Build a webhook evidence harness and add fixtures for DMs, shared posts, comments/reels/story replies; record ignored-event reason counts. |
| 2 | Message persistence | lab-only | 4 | Messages store direction, channel, Instagram message id, message type, text, raw payload, timestamps; duplicate Instagram message ids are ignored. | Proven retention policy, PII handling policy, migration validation on PostgreSQL, cross-shop data isolation evidence. | Raw payload stores PII and tokens if Meta payload includes sensitive fields; no archival/redaction evidence; SQLite tests may not catch PostgreSQL constraint/concurrency behavior. | DB schema evidence, sample persisted messages from realistic payloads, PII redaction review. | PostgreSQL integration tests for constraints, idempotency race, retention/redaction tests. | Add raw payload minimization/redaction tests and a realistic persistence validation script. |
| 3 | RabbitMQ worker pipeline | lab-only | 4 | Durable queues, retry/DLQ queues, worker consumer, prefetch=1, ack/nack/requeue, retry counter header, failed-job persistence after max retries. | End-to-end Docker Compose worker validation, retry-delay proof, back-pressure tests, graceful shutdown evidence, throughput/latency SLOs. | Retry code republishes to the main queue instead of publishing to the TTL retry queue, so configured retry delay may not be exercised; locked conversations can requeue hot-loop; payload `retry_count` differs from RabbitMQ header-based retry count. | Worker run logs, queue depth metrics, retry/DLQ drill report, performance chart. | Integration tests with real RabbitMQ for success, lock collision, retry delay, DLQ persistence, crash/restart. | Route retries through retry queue or document immediate retry; add jitter/backoff for lock contention; align retry_count in payload/header. |
| 4 | Redis conversation locking | lab-only | 4 | Redis `SET NX EX` lock with token-based Lua release; consumer serializes jobs per conversation. | Evidence under concurrent workers and lock expiry; lock heartbeat/long-run handling; observability for lock contention. | If an LLM/OpenAI call exceeds TTL, another worker can process same conversation; lock contention requeue can cause tight retry loops. | Concurrent worker test results with timestamps, TTL expiry drill. | Multi-worker integration tests, TTL-expiry tests, hot contention tests. | Add lock extension/heartbeat or TTL sized to p99 orchestration; add delayed requeue/backoff. |
| 5 | Product catalog | lab-only | 4 | Products, variants, size charts, API/frontend pages, seed data, semantic search support. | Real shop catalog import/export, bulk validation, media/image coverage, full-scale catalog performance. | Manual/demo catalog may not represent real fashion SKUs; no evidence for thousands of products/variants. | Realistic catalog fixture, import report, search/index benchmark. | Catalog CRUD with PostgreSQL, large catalog query tests, invalid SKU/price/currency tests. | Add a realistic 500-5,000 SKU catalog fixture and validation report. |
| 6 | Instagram post-to-product mapping | lab-only | 4 | Mapping by post URL/media id, multiple candidates, primary/display order, admin metadata, audit logs. | Real Instagram media URL normalization variants, carousel/multi-product workflows, ambiguous-product operator UX evidence. | URL normalization only trims trailing slash; query params, shortcode canonicalization, reels/permalinks may fail; multi-product mapping requires selection but user flow evidence is limited. | Resolver fixture pack covering post/reel/carousel URL forms and multi-product candidates. | URL canonicalization tests, carousel shared-post tests, ambiguous selection E2E. | Expand canonicalization and add Meta permalink/media-id contract tests. |
| 7 | Color/size normalization | lab-only | 4 | Persian/English aliases, shop/global aliases, fuzzy matching, numeric/free sizes, normalizer unit tests. | Real-world alias dataset, precision/recall metrics, category-specific size charts with Persian phrasing, false-positive review. | Fuzzy matching can over-normalize unknowns; limited built-in colors/sizes; shop aliases depend on exact cleaned values. | Normalization benchmark with labeled fashion messages. | Data-driven tests for 100+ colors/sizes, typos, multi-language, ambiguous values. | Create labeled normalization corpus and confidence thresholds; add admin workflow for reviewing misses. |
| 8 | Variant resolver | lab-only | 4 | Deterministic resolver owns matching, stock checks, confidence, mismatch reasons, alternatives, unavailable-demand logging. | Relevant-environment evidence with realistic variants, concurrent inventory, partial slot ambiguity, full operator workflow. | Resolver commits unavailable-demand logs inside resolution, creating side effects during reads/simulation-like paths; exact match can return a variant when only color or size is provided if one dimension is missing. | Resolver benchmark and mismatch taxonomy evidence. | Data-driven variant matrix tests, no-side-effect resolver tests, concurrent stock tests. | Separate pure resolution from logging; require explicit policy for partial matches; add resolver confidence calibration. |
| 9 | Inventory reservation/release | lab-only | 4 | Row lock via variant `get_for_update`, reserve/release endpoints, inventory movements, audit logs, order confirmation reserves inventory, cancellation/payment release/sale movements. | PostgreSQL concurrency proof, idempotent reservation per order, expiration release drill, full reserve->pay->sale accounting. | `_confirm_for_payment` calls reserve on each confirmation path; if order status/regression is mishandled duplicate reservations are possible; manual reserve commits twice; no load evidence. | Inventory ledger report, concurrent checkout test logs, expiration release report. | PostgreSQL concurrent reservation tests, order idempotency tests, payment/cancel/expire movement tests. | Add unique movement reference guard per order/variant/type and a reconciliation job/report. |
| 10 | LLM structured extraction | lab-only | 4 | OpenAI JSON-only prompt, Pydantic validation, fallback on JSON/validation/runtime errors, model/prompt version recorded in `AgentRun`. | Evaluation dataset, accuracy/latency/cost metrics, prompt regression suite, safety/adversarial tests, real API smoke tests. | Fallback `unclear` can silently continue without forcing human handoff; no model drift monitoring; no evidence of extraction quality on Persian commerce messages. | Labeled extraction eval with intent/slot F1, latency/cost report, red-team cases. | Offline golden eval with mocked model outputs; live smoke gated by env; malformed/adversarial tests. | Build extraction evaluation harness and set minimum F1/latency thresholds for TRL 5. |
| 11 | Conversation state machine | lab-only | 4 | Deterministic workflow states, state decisions based on intent/product/variant/customer fields/inventory/handoff. | End-to-end scenario matrix for complete buyer journey, cancellation, payment, stock-out, handoff, recovery. | Current logic may keep confirmation intent in `WAITING_FOR_CONFIRMATION` before payment unless exact current-state conditions are met; state transitions coupled with side-effect gating can create suggested replies without draft orders in simulation/preview. | State transition table, scenario run report, trace samples. | Golden state-machine tests for each state/intent combination and multi-turn E2E tests. | Formalize transition table and assertions; add scenario runner for representative DM transcripts. |
| 12 | Draft order creation | lab-only | 4 | Orchestrator creates/upserts waiting-confirmation orders when product/variant/customer info are complete and auto-send side effects are allowed; admin can create order from conversation. | Evidence that draft order is created under realistic confidence modes, preview modes, simulation modes, and operator workflows. | In copilot/preview/simulation, side effects are blocked, so draft-order creation may not occur even when operator expects an order draft; repeated upsert clears items. | Order creation scenario report across agent modes. | Tests for auto-send enabled/disabled, preview-required draft creation policy, operator create-order flow. | Define whether draft orders should be side effects independent of message auto-send; implement policy after evidence review. |
| 13 | Customer confirmation flow | lab-only | 4 | Order status waits for confirmation; `confirm_after_customer` moves to payment and reserves inventory; replies include confirmation/payment prompts. | Validated customer transcript flow, explicit confirmation detection accuracy, negative confirmation/cancel flows. | Confirmation depends on LLM intent and current workflow; no evidence for Persian yes/no variants or ambiguous confirmation. | Transcript suite with confirmations/refusals/edits. | Multi-turn E2E for confirm, change size after draft, cancel after draft, stock unavailable at confirm. | Add confirmation phrase corpus and deterministic guardrails for ambiguous confirmation. |
| 14 | Payment flow or mock payment | lab-only | 4 | Mock payment provider, payment URL, mock callback, idempotent callback handling, manual mark-paid, payment-link send. | Real provider integration or production-grade mock contract, callback signature/security, full callback E2E through admin/DM. | Mock pay endpoint is not equivalent to real provider; callback security is not representative; no settlement/refund/partial failure evidence. | Mock payment drill and provider-readiness checklist. | Mock callback idempotency, duplicate provider ref, failed payment, manual paid, payment link message tests. | Keep mock for TRL 5 but add provider interface contract tests and secured callback requirements for TRL 6. |
| 15 | Admin conversation inbox | lab-only | 4 | React routes/pages for conversations/detail, filters, priority, context panel, message thread, suggested reply actions, tests. | Browser E2E, accessibility, realistic operator workflow timing, multi-user takeover behavior. | Component tests alone do not prove full admin workflow; real API latency/loading/error states may be insufficient. | Playwright/Cypress run over Docker Compose, operator workflow screenshots. | E2E: login, filter inbox, open conversation, approve/edit reply, take over/release, create order. | Add browser E2E and operational UX checklist before TRL 5. |
| 16 | DM simulator | lab-only | 4 | Simulator API/page, simulation flag, no real outbound side effects, decision audit aggregation. | Scenario library, reproducible expected outcomes, realistic transcript replay, pass/fail scoring. | Simulator may not create orders because side effects are blocked by `is_simulation`; it can diverge from live behavior. | Simulator scenario pack and report comparing live-like vs simulation behavior. | Scenario tests for product mapping, variant mismatch, confirmation/payment, handoff. | Add simulator assertions and optional “dry-run order preview” artifacts. |
| 17 | Human handoff | lab-only | 4 | Handoff service, conversation flags/state, take-over/release/assign/resolve APIs, admin UI controls, audit logs/events. | Multi-operator concurrency, escalation SLA evidence, notification/alerting, handoff reason taxonomy metrics. | Agent pause/assignment prevents processing but queued jobs may still pile; no evidence for operator notification latency. | Handoff drill with two operators, audit/event timeline. | Concurrent takeover tests, release-to-agent resumes agent tests, notification/priority tests. | Add optimistic concurrency/versioning and handoff SLA dashboard. |
| 18 | Decision trace and audit logs | lab-only | 4 | `AgentRun`, `AgentAction`, `AgentDecisionAudit`, conversation events, admin audit logs for key actions. | Complete trace coverage map, immutable audit guarantees, PII review, export/debug tooling. | Multiple trace tables can disagree; no schema-level immutability; raw prompts/replies may include PII. | Traceability report linking inbound message -> extraction -> state -> reply -> order/payment. | Tests asserting trace rows for each workflow step and PII masking/export behavior. | Define one canonical trace view and add redaction/export controls. |
| 19 | Analytics | lab-only | 4 | Funnel, posts, post revenue, lost demand, operator performance, handoff/response, agent performance; frontend analytics pages/tests. | Metric definitions validated against realistic data, time-zone correctness, large data performance, BI export. | Some metrics derive post performance from conversation slots, not direct message attribution; missing baseline/expected report for demo scenario. | Analytics fixture report with known expected numbers. | Deterministic analytics tests over seeded full journey, performance tests for large datasets. | Add metric specification and golden analytics fixture. |
| 20 | Failed job handling | lab-only | 4 | Failed job model/service/API, DLQ persistence, retry/ignore with admin audit, platform scoped jobs. | Real RabbitMQ DLQ drill, retry-to-success proof, unscoped-job ownership policy, alerting. | `handle_delivery` records a failure on every exception before worker retry logic, which can create failed-job records before max retries; duplicate records possible. | Failure drill report showing counts, DLQ state, admin retry. | Integration tests for one transient failure, max retries, retry action, ignore action. | Persist failed jobs only at terminal DLQ or mark transient separately; add alerting and dedupe key. |
| 21 | Security and shop isolation | lab-only | 4 | JWT auth, password hashing, shop membership/role dependencies, token encryption, optional webhook signature, rate limits, CORS env. | Pen-test checklist, row-level isolation tests across every endpoint, secret rotation, production CORS/security headers, webhook replay protection. | No DB row-level security; isolation relies on service filters; some internal services can bypass user checks; weak local default secrets could leak to non-local env if misconfigured. | Security test report and endpoint access matrix. | Cross-shop API tests for all resources, role tests for mutation endpoints, webhook replay/signature tests, secret config tests. | Add automated endpoint isolation matrix and fail startup for insecure production secrets. |
| 22 | Tests and documentation | lab-only | 4 | 169 backend pytest tests discovered, many targeted sprint docs, operator/admin/production/API docs, frontend tests in package. | Evidence plan, TRL-specific acceptance suite, latest test run artifacts, integration/E2E/load tests, documented SLOs. | Test suite appears broad but lab-heavy; frontend test count command needs npm tooling to run; no single evidence matrix mapping capabilities to tests/artifacts. | This assessment document, CI report, coverage report, Docker Compose E2E report. | Run full backend pytest, frontend vitest/typecheck, docker-compose smoke, Playwright, load tests. | Create evidence CI workflow and keep artifacts under `docs/evidence/` or CI build artifacts. |

## C. Critical blockers above TRL 4

1. **No relevant-environment evidence pack:** there is no reproducible test run proving webhook -> RabbitMQ -> worker -> orchestrator -> admin/order/payment behavior in Docker Compose with PostgreSQL, Redis, RabbitMQ, Qdrant, and OpenAI mocked only at external boundaries.
2. **No realistic data validation:** product catalog, Instagram payloads, Persian/English commerce messages, variant aliases, and confirmation/payment transcripts are not benchmarked against labeled realistic data.
3. **Queue/locking reliability gaps:** retry behavior, lock contention, lock TTL expiration, and DLQ handling need integration evidence and may need code changes before TRL 5 evidence can pass.
4. **LLM extraction has no measured quality bar:** no prompt regression harness, accuracy targets, latency/cost thresholds, or drift checks exist for the key AI component.
5. **Operator workflow lacks browser E2E evidence:** admin inbox, suggested replies, handoff, simulator, mapping, and order/payment flows need full browser-backed scenario tests.
6. **Payment is mock-only:** acceptable for TRL 5 if explicitly scoped, but TRL 6 needs provider contract, secured callbacks, settlement/failure handling, or pilot-approved manual payment controls.
7. **Security/isolation evidence incomplete:** role checks exist, but every endpoint and data path needs a cross-shop isolation matrix and production secret/CORS/webhook replay checks.
8. **Analytics and traceability need golden reports:** metrics and audits exist, but there is no canonical trace/evidence report proving calculations and trace completeness.

## D. TRL 5 acceptance checklist

TRL 5 target: **end-to-end software tested in a relevant environment with realistic data, realistic integrations, realistic workflows, and measurable performance.**

- [ ] Docker Compose evidence stack runs PostgreSQL, Redis, RabbitMQ, Qdrant, backend, worker, scheduler, and frontend.
- [ ] Alembic migrates a clean PostgreSQL database to head and seeds a realistic generic catalog.
- [ ] Webhook contract tests replay realistic Instagram DM/shared-post/comment/story payloads and validate persistence/queueing.
- [ ] End-to-end worker test processes at least 25 realistic conversations from inbound message to suggested reply/order/payment/handoff outcomes.
- [ ] LLM extraction evaluation runs on a labeled transcript corpus with minimum agreed intent accuracy, slot F1, and structured JSON validity.
- [ ] Variant resolver benchmark runs on realistic product variants and alias corpus with documented precision/recall and mismatch behavior.
- [ ] Inventory concurrency tests prove no oversell under simultaneous reservation attempts on PostgreSQL.
- [ ] Mock payment flow proves payment link creation, callback paid/failed/idempotent duplicate behavior, and manual mark-paid flow.
- [ ] Admin browser E2E proves login, shop selection, inbox triage, suggested reply approval/edit/reject, handoff take/release, mapping, order detail, analytics, and failed-job retry/ignore.
- [ ] Failed-job drill proves transient retry, max-retry DLQ, persistence, admin retry, and audit logs.
- [ ] Security matrix proves cross-shop isolation and role enforcement for all critical endpoints.
- [ ] Performance report records p50/p95 webhook ack latency, worker processing latency, LLM latency, queue depth under burst, admin page load, and error rate.
- [ ] Evidence artifacts are versioned or attached to CI with command logs and test results.

## E. TRL 6 pilot-readiness checklist

TRL 6 target: **pilot-ready prototype demonstrated on realistic full-scale scenarios with operational constraints.**

- [ ] Pilot runbook defines onboarding, catalog import, Instagram account setup, webhook verification, handoff operations, payment mode, escalation, rollback, and support contacts.
- [ ] Pilot environment has production-like secrets, restricted CORS, webhook signature/replay protection, encrypted tokens, backups, and monitoring.
- [ ] SLOs are defined and monitored: webhook ack availability, end-to-end response latency, worker queue lag, failed-job rate, handoff SLA, payment conversion, and admin uptime.
- [ ] Load test covers full-scale pilot scenario: expected daily DM volume, bursts, concurrent operators, catalog size, and queue recovery after outage.
- [ ] Human-in-the-loop policy is configured for first orders, low confidence, high value, payment disputes, angry customers, stock mismatch, and unsupported requests.
- [ ] Payment approach is pilot-approved: real provider integration with secured callbacks or operationally controlled manual/mock payment process with documented limitations.
- [ ] Data protection controls cover PII minimization, retention, audit export, access review, token rotation, and incident response.
- [ ] Observability dashboards and alerts cover health/readiness, queue lag, DLQ/failed jobs, LLM failures, response latency, inventory exceptions, and webhook errors.
- [ ] Disaster drills prove Redis/RabbitMQ/PostgreSQL restart recovery and no lost/duplicated order side effects.
- [ ] Pilot acceptance report demonstrates at least one complete shop scenario at realistic scale with known success metrics and unresolved risks signed off.

## F. Evidence matrix

| Capability | Evidence artifact | Test name | Owner | Status |
|---|---|---|---|---|
| Instagram webhook ingestion | `docs/evidence/webhook-contract-report.md` | `test_instagram_webhook_contract_realistic_payloads` | Backend | Missing |
| Message persistence | `docs/evidence/message-persistence-postgres.md` | `test_message_persistence_idempotent_postgres` | Backend | Missing |
| RabbitMQ worker pipeline | `docs/evidence/rabbitmq-worker-drill.md` | `test_worker_processes_message_in_compose` | Backend/DevOps | Missing |
| Redis conversation locking | `docs/evidence/redis-lock-contention.md` | `test_two_workers_do_not_process_same_conversation` | Backend/DevOps | Missing |
| Product catalog | `docs/evidence/catalog-fixture-validation.md` | `test_realistic_catalog_import_and_query_performance` | Backend/Admin | Missing |
| Instagram post mapping | `docs/evidence/post-mapping-contract.md` | `test_resolve_post_reel_carousel_url_variants` | Backend/Admin | Missing |
| Color/size normalization | `docs/evidence/normalization-benchmark.md` | `test_normalization_labeled_corpus_metrics` | AI/Backend | Missing |
| Variant resolver | `docs/evidence/variant-resolver-benchmark.md` | `test_variant_resolver_realistic_matrix` | Backend | Missing |
| Inventory reservation/release | `docs/evidence/inventory-concurrency-report.md` | `test_concurrent_reservations_do_not_oversell_postgres` | Backend | Missing |
| LLM structured extraction | `docs/evidence/llm-extraction-eval.md` | `test_llm_extraction_golden_corpus` | AI | Missing |
| Conversation state machine | `docs/evidence/state-machine-scenario-report.md` | `test_order_conversation_state_matrix` | Backend/AI | Missing |
| Draft order creation | `docs/evidence/order-draft-flow.md` | `test_complete_slots_create_expected_draft_order` | Backend | Missing |
| Customer confirmation | `docs/evidence/confirmation-flow-transcripts.md` | `test_customer_confirmation_moves_order_to_payment` | Backend/AI | Missing |
| Mock payment | `docs/evidence/mock-payment-drill.md` | `test_mock_payment_paid_failed_duplicate_callbacks` | Backend | Missing |
| Admin inbox | `docs/evidence/admin-inbox-e2e.md` | `e2e_admin_inbox_triage_and_reply` | Frontend | Missing |
| DM simulator | `docs/evidence/dm-simulator-scenarios.md` | `test_simulator_runs_named_scenarios_with_expected_outcomes` | AI/Frontend | Missing |
| Human handoff | `docs/evidence/handoff-drill.md` | `e2e_operator_takeover_release_assign_resolve` | Frontend/Backend | Missing |
| Decision trace/audit | `docs/evidence/decision-trace-coverage.md` | `test_trace_links_inbound_to_reply_order_payment` | Backend | Missing |
| Analytics | `docs/evidence/analytics-golden-report.md` | `test_analytics_golden_fixture_metrics` | Backend/Data | Missing |
| Failed jobs | `docs/evidence/failed-job-drill.md` | `test_failed_job_retry_dlq_and_admin_actions` | Backend/DevOps | Missing |
| Security/shop isolation | `docs/evidence/security-isolation-matrix.md` | `test_all_endpoints_enforce_shop_isolation_and_roles` | Backend/Security | Missing |
| Documentation | `docs/evidence/trl5-ci-run.md` | `test_documented_commands_match_ci` | Tech Lead | Missing |

## G. Recommended implementation sprints

### Sprint 1 — Evidence harness and realistic fixtures (TRL 5 foundation)

- Create `docs/evidence/` artifact structure and CI job that stores backend, frontend, Docker Compose, and benchmark logs.
- Add realistic seed catalog: products, variants, colors/sizes, inventory, post mappings, customers, and transcript fixtures.
- Add webhook contract fixtures for current Meta Instagram payload types used by the product.
- Define metric thresholds for TRL 5: webhook ack p95, worker p95, extraction accuracy, resolver accuracy, queue recovery, admin E2E pass rate.

### Sprint 2 — Backend relevant-environment integration suite

- Add PostgreSQL/RabbitMQ/Redis/Qdrant-backed tests or Compose smoke scripts for webhook-to-worker processing.
- Add RabbitMQ retry/DLQ drill and fix retry queue/backoff behavior if evidence fails.
- Add Redis lock contention and TTL expiry tests; implement lock extension or safer TTL policy if needed.
- Add PostgreSQL inventory concurrency tests and reservation idempotency guard if evidence fails.

### Sprint 3 — AI and fashion validation

- Build labeled extraction corpus for Persian/English commerce messages.
- Add LLM prompt regression harness with mocked outputs and optional live OpenAI smoke test.
- Add color/size normalization and variant resolver benchmarks with confusion/error reports.
- Add state-machine transcript runner for full customer journeys, stock-outs, edits, cancellations, and handoffs.

### Sprint 4 — Admin/browser E2E and operator evidence

- Add Playwright/Cypress E2E against Docker Compose.
- Cover login, shop selection, inbox filters, conversation detail, suggested reply approval/edit/reject, handoff, order creation/payment link, post mapping, failed jobs, simulator, and analytics.
- Capture screenshots/video artifacts for pilot demos.
- Add accessibility and loading/error-state checks for operator-critical pages.

### Sprint 5 — TRL 5 acceptance run and remediation

- Run the full TRL 5 suite in CI and locally via Docker Compose.
- Produce evidence artifacts for each matrix row.
- Fix blockers discovered by evidence runs: queue retry semantics, lock TTL, idempotency, endpoint isolation, metric correctness, or UX defects.
- Publish TRL 5 acceptance report with residual risks and explicit mock-payment scope.

### Sprint 6 — TRL 6 pilot readiness

- Build pilot runbook, monitoring dashboards, alert thresholds, backup/restore procedure, and incident response.
- Harden production configuration: secret checks, CORS, webhook replay/signature requirements, token rotation, PII retention/redaction.
- Add load test using pilot-scale DM volume, catalog size, and operator concurrency.
- Decide payment mode for pilot: real provider contract tests or documented manual/mock payment operational controls.
- Execute full pilot demo at realistic scale and create pilot acceptance report.

## H. Commands to run locally

Run these commands from the repository root unless noted otherwise.

```bash
# Inspect repository and tests
rg --files -g '!node_modules' -g '!**/.git/**'
rg -n "def test_" backend/app/tests | wc -l

# Backend unit/API tests
cd backend
pytest
ruff check .
alembic upgrade head

# Frontend checks
cd frontend
npm install
npm run typecheck
npm test
npm run build

# Full local stack smoke
docker compose up --build
curl http://localhost:8800/health
curl http://localhost:8800/ready
docker compose ps
docker compose logs -f backend worker scheduler

# Seed and demo evidence
docker compose exec backend python -m app.scripts.seed
docker compose exec backend python -m app.scripts.seed_demo_data

# Targeted current suites to start evidence collection
cd backend && pytest app/tests/test_webhook_ingestion.py app/tests/test_message_consumer.py app/tests/test_redis_lock.py -q
cd backend && pytest app/tests/test_llm_extraction_service.py app/tests/test_state_machine_service.py app/tests/test_order_agent_flow.py -q
cd backend && pytest app/tests/test_inventory_service.py app/tests/test_orders_api.py app/tests/test_analytics_api.py app/tests/test_sprint_f.py -q
cd frontend && npm test -- ConversationsPage DMSimulatorPage SystemHealthPage AnalyticsPage
```
