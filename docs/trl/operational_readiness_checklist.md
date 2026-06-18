# Operational Readiness Checklist — TRL 6 Pilot

**Assessment date:** 2026-06-09  
**Usage:** Complete before pilot go-live. Mark each item: ✅ Done / ⚠️ Partial / ❌ Missing / N/A

---

## Deployment readiness

| # | Item | Status | Evidence / notes |
|---|------|--------|------------------|
| 1 | Docker Compose or production deployment documented | ⚠️ Partial | `docs/production-deployment.md`, `docker-compose.yml` |
| 2 | Alembic migrations apply cleanly on PostgreSQL | ⚠️ Partial | `test_migrations.py`; no archived migrate log |
| 3 | Backend, worker, scheduler services defined | ✅ Present | `docker-compose.yml` |
| 4 | Environment variables documented | ✅ Present | `.env.example`, `docs/environment-variables.md` |
| 5 | Health (`/health`) and readiness (`/api/v1/ready`) probes configured | ✅ Present | `backend/app/api/v1/health.py` |
| 6 | Production secrets validated (JWT, encryption, OpenAI) | ❌ Missing | No startup fail-for-weak-secrets evidence |
| 7 | CORS restricted for production | ❌ Missing | `CORS_ORIGINS` documented; pilot env not evidenced |

---

## Security readiness

| # | Item | Status | Evidence / notes |
|---|------|--------|------------------|
| 1 | JWT auth on admin APIs | ✅ Present | `test_auth_api.py` |
| 2 | Shop membership / role checks | ✅ Present | `test_roles.py`, `require_shop_role` |
| 3 | Instagram tokens encrypted at rest | ✅ Present | Fernet encryption in Sprint 7 |
| 4 | Optional Meta webhook signature verification | ✅ Present | `META_APP_SECRET` |
| 5 | Rate limiting on login, webhook, outbound | ✅ Present | Sprint 7 security |
| 6 | Audit logging for sensitive actions | ✅ Present | `AdminAuditLog`, Sprint F docs |
| 7 | Cross-shop isolation matrix (all endpoints) | ❌ Missing | Partial tests only |
| 8 | PII minimization / log masking review | ⚠️ Partial | `log_masking.py`; no formal review |
| 9 | Webhook replay protection | ❌ Missing | Not evidenced |

---

## Data readiness

| # | Item | Status | Evidence / notes |
|---|------|--------|------------------|
| 1 | Real product catalog configured | ⚠️ Partial | TRL demo seed for lab; pilot needs real shop data |
| 2 | Variants with SKU, color, size, stock, price | ✅ Present | Seed + admin UI |
| 3 | Instagram post-to-product mapping ≥ 80% | ⚠️ Partial | TRL seed maps 100%; pilot shop TBD |
| 4 | Color/size aliases for shop language | ✅ Present | `seed_trl_demo_data` Persian aliases |
| 5 | Demo data isolated (`is_simulation`) | ✅ Present | Simulation flags in models |
| 6 | Database backup procedure | ❌ Missing | Not in repo |
| 7 | Data retention / export policy | ❌ Missing | Not in repo |

---

## Operator readiness

| # | Item | Status | Evidence / notes |
|---|------|--------|------------------|
| 1 | Owner/admin/operator assigned to shop | ✅ Present | Pilot criterion; TRL seed creates operator |
| 2 | Handoff policy configured | ✅ Present | `ShopAgentSettings.handoff_policy_json` |
| 3 | Support contact in agent/risk policy | ⚠️ Partial | Checked in pilot checklist |
| 4 | Agent Studio mode appropriate for pilot | ⚠️ Partial | Controlled autopilot + preview settings |
| 5 | Operator trained on inbox, handoff, orders | ❌ Missing | Runbook only (`docs/pilot_test_script.md`) |
| 6 | Daily pilot review process defined | ✅ Present | `docs/pilot_test_script.md`, `docs/trl/pilot_plan.md` |
| 7 | Emergency stop tested by operator | ⚠️ Partial | API tested; requires human drill before pilot |

---

## Integration readiness

| # | Item | Status | Evidence / notes |
|---|------|--------|------------------|
| 1 | Instagram business account connected | ⚠️ Partial | Admin UI; TRL demo uses simulated account |
| 2 | Meta webhook subscribed (messages) | ❌ Missing | `docs/meta-webhook-setup.md` — pilot-specific proof needed |
| 3 | ngrok or public HTTPS callback for dev | ✅ Documented | README Meta section |
| 4 | RabbitMQ queues (main, retry, DLQ) | ✅ Present | Sprint F docs |
| 5 | Redis available for locks/rate limits | ✅ Present | Compose + tests |
| 6 | Qdrant for semantic search | ✅ Present | Readiness check includes qdrant |
| 7 | OpenAI API key configured | ⚠️ Partial | Readiness checks config presence, not quality |
| 8 | Real Instagram send disabled for lab (`ENABLE_REAL_PROVIDER_SEND=false`) | ✅ Present | Env documented |

---

## Monitoring readiness

| # | Item | Status | Evidence / notes |
|---|------|--------|------------------|
| 1 | Structured JSON logs with request_id | ✅ Present | Sprint 7 |
| 2 | Prometheus metrics endpoint | ✅ Present | `GET /api/v1/metrics` |
| 3 | System health admin page | ✅ Present | `/system-health` |
| 4 | Pilot metrics API | ✅ Present | `GET /api/v1/shops/{id}/pilot/metrics` |
| 5 | Failed jobs admin UI + API | ✅ Present | Sprint F |
| 6 | Alerting on DLQ / failed jobs / readiness failure | ❌ Missing | No alert rules in repo |
| 7 | Dashboards for queue lag, LLM errors, handoff SLA | ❌ Missing | Metrics exist; dashboards not evidenced |
| 8 | Pilot event log reviewed daily | ⚠️ Partial | `GET /pilot/events`; process in pilot plan |

---

## Rollback readiness

| # | Item | Status | Evidence / notes |
|---|------|--------|------------------|
| 1 | Emergency stop API + UI | ✅ Present | `POST .../pilot/emergency-stop` |
| 2 | Resume automation API | ✅ Present | `POST .../pilot/resume` |
| 3 | Disable pilot mode in settings | ✅ Present | Pilot settings API |
| 4 | Switch agent to copilot/human-first | ✅ Present | Agent Studio modes |
| 5 | Pause worker consumption procedure | ⚠️ Partial | Documented in pilot test script |
| 6 | Failed job manual resolution procedure | ✅ Present | Sprint F operator guide |
| 7 | Customer communication templates | ⚠️ Partial | Recovery rules; incident templates incomplete |
| 8 | Rollback drill executed and logged | ❌ Missing | No drill report |

---

## Support readiness

| # | Item | Status | Evidence / notes |
|---|------|--------|------------------|
| 1 | Operator guide | ✅ Present | `docs/operator-guide.md` |
| 2 | Admin guide | ✅ Present | `docs/admin-guide.md` |
| 3 | Troubleshooting guide | ✅ Present | `docs/troubleshooting.md` |
| 4 | API reference | ✅ Present | `docs/api.md` |
| 5 | On-call rotation / escalation contacts | ❌ Missing | Define per pilot |
| 6 | Incident severity classification | ✅ Present | `docs/pilot_test_script.md` |
| 7 | Post-incident review template | ❌ Missing | Add after first pilot incident |

---

## Gate summary

| Category | Done | Partial | Missing |
|----------|-----:|--------:|--------:|
| Deployment | 4 | 2 | 1 |
| Security | 6 | 1 | 2 |
| Data | 4 | 2 | 2 |
| Operator | 3 | 3 | 1 |
| Integration | 4 | 3 | 1 |
| Monitoring | 5 | 1 | 2 |
| Rollback | 5 | 2 | 1 |
| Support | 5 | 0 | 2 |

**Pilot go-live recommendation:** Resolve all ❌ Missing items marked P1 in `test_coverage_summary.md` and pass TRL 5 validation with archived report before setting `pilot_enabled=true` for real customer traffic.
