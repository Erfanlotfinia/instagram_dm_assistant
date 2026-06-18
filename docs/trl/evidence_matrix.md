# TRL Evidence Matrix — Modira

**Assessment date:** 2026-06-09  
**Legend:** Status = `Present` (in-repo evidence), `Partial` (implemented but evidence incomplete), `Missing` (not evidenced)

| Capability | Component | TRL target | Evidence artifact | Test coverage | Validation result | Owner | Status | Notes |
|------------|-----------|:----------:|-------------------|---------------|-------------------|-------|--------|-------|
| Instagram webhook ingestion | `WebhookIngestionService`, `integrations/instagram_webhook.py`, `api/v1/webhooks` | 5 | Code + `test_webhook_ingestion.py`, `test_webhook_api.py` | 10 tests | Not run in TRL runner | Backend | Partial | Idempotency by `instagram_message_id`; Meta signature optional; no archived webhook contract report |
| Message processing | `workers/message_consumer.py`, `ConversationOrchestrator` | 5 | Code + `test_message_consumer.py`, `test_conversation_orchestrator.py` | 4 tests | Exercised per TRL scenario | Backend | Partial | Redis lock serialization; RabbitMQ retry/DLQ not in TRL metrics |
| LLM extraction | `LLMExtractionService` | 5 | Code + `test_llm_extraction_service.py`, `test_agent_safety_controls.py` | 8 tests | **Not used in TRL runner** | AI/Backend | Partial | TRL uses `RuleBasedTRLExtractionService`; no F1/latency eval archived |
| Safe fallback | `LLMExtractionService`, orchestrator safe_fallback | 5 | `test_agent_safety_controls.py` | 6 tests | `invalid_llm_json_handled_rate` hardcoded 1.0 | AI/Backend | Partial | Invalid JSON → unclear intent + handoff tested in unit tests only |
| Product mapping | `InstagramProductResolver`, `InstagramProductMap` | 5 | `test_instagram_product_maps_api.py`, TRL scenarios with `shared_post_url` | 8+ tests | Per-scenario in TRL runner | Backend/Admin | Partial | 20 post URLs in TRL seed; multi-product `TRLMULTI` scenario |
| Color normalization | `ColorSizeNormalizer`, `ColorAlias` | 5 | `test_sprint_a_normalization_unit.py`, TRL scenarios | 3+ tests | Slot accuracy in TRL metrics | Backend | Partial | Persian/English aliases in TRL seed; no precision/recall benchmark |
| Size normalization | `ColorSizeNormalizer`, `SizeAlias` | 5 | `test_sprint_a_normalization_unit.py`, TRL scenarios | 3+ tests | Slot accuracy in TRL metrics | Backend | Partial | Fashion sizes XS–XL in seed |
| Variant resolver | `VariantResolver` / variant service | 5 | `test_variants_api.py`, `test_inventory_service.py` | 11 tests | `variant_resolution_accuracy` in TRL | Backend | Partial | Out-of-stock and mismatch scenarios in TRL corpus |
| Inventory reservation | `InventoryService` | 5 | `test_inventory_service.py`, order flow tests | 6 tests | `inventory_double_reservation_count` hardcoded 0 | Backend | Partial | Row-lock reserve; no concurrent PostgreSQL evidence |
| Order creation | `OrderService`, orchestrator | 5 | `test_order_service.py`, `test_order_agent_flow.py`, TRL scenarios | 9+ tests | `false_order_creation_count` in TRL | Backend | Partial | Draft on complete slots; simulation mode differs from live |
| Customer confirmation | State machine + orchestrator | 5 | `test_state_machine_service.py`, `test_sprint7_e2e.py` | 12 tests | TRL confirm scenarios | Backend | Partial | Explicit confirm before payment enforced in code |
| Payment handling | `PaymentService`, mock provider | 5 | `test_sprint7_e2e.py`, orders API tests | 8+ tests | `false_payment_status_change_count` hardcoded 0 | Backend | Partial | Mock only; idempotent callback in E2E test |
| Human handoff | `HandoffService` | 5 | `test_handoff_service.py`, TRL handoff scenarios | 3+ tests | `handoff_precision`/`recall` in TRL | Backend/Frontend | Partial | Take-over/release APIs + UI |
| Admin inbox | `ConversationsPage`, conversation APIs | 5 | `test_conversations_api.py`, `ConversationsPage.test.tsx` | 5 tests | Manual Sprint 6 checklist | Frontend | Partial | No Playwright E2E |
| DM simulator | `DMSimulatorService`, `api/v1/simulator` | 5 | `test_sprint_e_simulator.py`, `DMSimulatorPage.test.tsx` | 6 tests | Not scored in TRL runner | AI/Frontend | Partial | Simulation blocks some side effects vs live |
| TRL validation runner | `TRLValidationRunner`, `api/v1/trl_validation` | 5 | `test_trl_validation.py`, `TRLValidationPage.tsx` | 7 backend + 4 frontend | **No archived run** | Tech Lead | Partial | 100 scenarios; thresholds defined; DB-persisted runs |
| Decision trace | `AgentRun`, `AgentDecisionTrace`, `DecisionTraceViewer` | 5 | Orchestrator writes traces; frontend viewer | Indirect via TRL/orchestrator tests | Per-scenario `risk_score` in TRL | Backend | Partial | No trace completeness audit report |
| Audit logs | `AdminAuditLog`, `AuditService` | 5 | `test_sprint7_security.py`, pilot audit events | 2+ tests | Pilot criterion `audit_logging_enabled` | Backend/Security | Partial | Key actions logged; no export/PII review |
| Analytics | Analytics APIs + pages | 5 | `test_analytics_api.py`, `test_sprint_f.py`, frontend tests | 12+ tests | Not in TRL thresholds | Backend/Data | Partial | Funnel, lost demand, agent performance |
| Readiness checks | `api/v1/health`, `PilotService.readiness` | 6 | `test_health.py`, `test_pilot_readiness.py` | 9 tests | `/ready` + pilot criteria | DevOps | Partial | Postgres/redis/rabbitmq/qdrant/openai config |
| Failed job handling | `FailedJobService`, DLQ | 6 | `test_sprint_f.py` | 10 tests | Pilot criterion `no_critical_failed_jobs` | Backend/DevOps | Partial | Admin retry/ignore; no DLQ drill report |
| Pilot emergency stop | `PilotService.set_emergency_stop` | 6 | `test_pilot_readiness.py`, `PilotReadinessPage` | 3 tests | Blocks auto-send/orders when enabled | Ops | Present | API + UI; requires operator test before pilot |

---

## Threshold cross-reference

TRL runner thresholds (`backend/app/services/trl_validation_runner.py`):

```
intent_accuracy ≥ 0.90
slot_extraction_accuracy ≥ 0.85
product_resolution_accuracy ≥ 0.90
variant_resolution_accuracy ≥ 0.85
false_order_creation_count ≤ 0
false_payment_status_change_count ≤ 0  [stubbed]
inventory_double_reservation_count ≤ 0  [stubbed]
invalid_llm_json_handled_rate = 1.0      [stubbed]
duplicate_webhook_idempotency_rate = 1.0 [stubbed]
critical_security_tests_pass_rate = 1.0  [stubbed]
```

---

## Pilot readiness criteria cross-reference

From `PilotService._criteria` (`backend/app/services/pilot_service.py`):

1. Latest TRL validation run passed thresholds
2. No critical failed jobs
3. `/ready` is ok
4. Operator assigned
5. Handoff policy configured
6. Emergency stop tested
7. Product mapping coverage ≥ threshold (default 80%)
8. Inventory verified within 24h
9. Payment mode configured
10. Audit logging enabled

**Known gap:** criterion 1 checks `status == "passed"` but TRL runner sets `status == "completed"`.
