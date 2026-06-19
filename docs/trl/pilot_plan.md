# TRL 6 Pilot Plan — Modira

**Version:** 1.0  
**Date:** 2026-06-09  
**Status:** Draft — not yet executed

---

## Pilot objective

Demonstrate the Modira under **constrained real-world operations** for one fashion shop: accurate variant resolution, safe automation with human oversight, measurable conversion metrics, and proven rollback via emergency stop — without unacceptable customer harm or inventory/payment errors.

**Success means:** completing the pilot window with no unresolved critical incidents, TRL validation thresholds met at start, and daily metrics within agreed bounds.

---

## Pilot scope

### In scope

- Instagram DM and shared-post order conversations for **one pilot shop**
- **Controlled autopilot** with preview/low-confidence gates and daily caps
- Mock payment or operator-approved manual payment (pilot mode TBD)
- Human handoff for complaints, payment disputes, ambiguous variants, high risk
- Admin monitoring: inbox, pilot readiness, system health, analytics, failed jobs
- TRL validation re-run if catalog or agent settings change materially

### Out of scope

- Multi-shop rollout
- Comments/reels/ad triggers at full scale (unless pre-mapped and tested)
- Real payment settlement/refunds (unless provider integrated and tested)
- Unsupervised 24/7 full autopilot without operator coverage
- Load beyond agreed daily message/order caps

---

## Selected shop profile

| Field | Planned value | Status |
|-------|---------------|--------|
| Shop slug | `trl-commerce-demo` (lab) → **real pilot shop TBD** | **MISSING** |
| Instagram account | Single connected business account | Configure in admin |
| Currency | Shop-local (e.g. IRR) | Per shop settings |
| Catalog size | ≥ 10 active products, ≥ 80% mapped | Per readiness API |
| Languages | Persian primary, English supported | Agent settings |
| Agent mode | `CONTROLLED_AUTOPILOT` | Agent Studio |

**Lab credentials (development only):**

- Admin: `trl-admin@example.com` / `Password123!`
- Operator: `trl-operator@example.com` / `Password123!`
- Shop slug: `trl-commerce-demo`

---

## Allowed products

Configure via pilot settings (`allowed_product_ids`, `allowed_instagram_account_ids`):

| Rule | Setting |
|------|---------|
| Default | All active mapped products (if `allowed_product_ids` is null) |
| Restricted pilot | Explicit UUID list of ≤ 10 hero SKUs |
| Non-allowed product request | Preview or handoff — no auto order progression |

**Pre-pilot requirement:** ≥ 80% active product mapping coverage (`product_mapping_threshold` on readiness API).

---

## Success criteria

| # | Criterion | Measurement |
|---|-----------|-------------|
| 1 | TRL validation thresholds passed within 7 days of pilot start | `trl-validation` run `thresholds_passed` all true |
| 2 | `/api/v1/ready` returns `ok` throughout pilot window | Health monitoring |
| 3 | Zero unresolved critical failed jobs | `no_critical_failed_jobs` criterion |
| 4 | No false paid orders or double inventory deduction | Order audit + inventory movements |
| 5 | Emergency stop halts automation within one request | API/UI test + event log |
| 6 | Daily caps enforced (auto-send, auto-order) | Pilot events `auto_send_limit_reached` |
| 7 | Handoffs resolved within operator SLA (define: e.g. 30 min business hours) | Inbox metrics |
| 8 | ≥ 90% variant resolution on in-scope products (manual sample review) | Operator audit sample |
| 9 | Complete daily metrics and event log for each pilot day | Pilot metrics API |

---

## Failure criteria (stop or rollback)

| # | Trigger | Action |
|---|---------|--------|
| 1 | Any unauthorized auto-send after emergency stop | Immediate stop + incident review |
| 2 | Order created for wrong variant/SKU confirmed by customer | Stop + manual order review |
| 3 | Payment marked paid without confirmation | Stop + payment audit |
| 4 | Critical failed job unresolved > 4 hours | Stop worker if needed |
| 5 | `/ready` failed > 15 minutes | Pause pilot traffic |
| 6 | TRL validation regression (threshold fail on re-run) | Disable autopilot |
| 7 | Customer complaint cluster (≥ 3 similar in 24h) | Emergency stop + owner review |

---

## Incident plan

### Severity levels

| Level | Examples | Response |
|-------|----------|----------|
| Info | Preview created, cap approached | Log only |
| Warning | Failed job (transient), low mapping coverage | Operator notify |
| Error | Repeated worker failures, payment callback errors | On-call investigate |
| Critical | Wrong order/payment, emergency stop failure, data leak | **Emergency stop first**, then investigate |

### Response steps

1. Activate **Emergency stop** (`POST /api/v1/shops/{id}/pilot/emergency-stop` or Pilot Readiness UI)
2. Assign open conversations to operators
3. Capture IDs: conversations, orders, payments, failed jobs, pilot events
4. Root cause analysis within 24h for Error+; 4h for Critical
5. Resume only when `ready_for_trl6_pilot` is true and pilot owner approves

See also: `docs/pilot_test_script.md` — Incident handling section.

---

## Daily monitoring checklist

- [ ] Check `GET /api/v1/shops/{id}/pilot-readiness` — resolve warnings
- [ ] Review pilot metrics: inbound, auto-sent, previews, handoffs, orders, paid, failed jobs, LLM errors, p95 latency
- [ ] Review pilot events (warning/error/critical)
- [ ] Check system health and failed jobs page
- [ ] Confirm inventory movements in last 24h
- [ ] Spot-check 5 conversations for trace quality and reply appropriateness
- [ ] Confirm operators scheduled for next window
- [ ] Owner decision: continue / pause / expand / rollback

---

## Pilot duration

| Phase | Duration | Activities |
|-------|----------|------------|
| **Prep** | 3–5 days | Seed real catalog, mapping, TRL full run, emergency stop drill, readiness true |
| **Constrained pilot** | 14 days | Daily caps, first-50-order approval, operator coverage business hours |
| **Review** | 2 days | Metrics analysis, incident retrospective, TRL 6 acceptance report |
| **Total** | ~3 weeks | Adjustable based on traffic |

---

## Exit criteria

### Continue to broader rollout (TRL 6 pass)

- All success criteria met for ≥ 10 pilot days
- No Critical incidents in final 7 days
- Owner sign-off on residual risks
- Documented payment approach acceptable for next phase
- Load test plan scheduled for TRL 7

### Pause or fail

- Any failure criterion triggered without satisfactory mitigation
- TRL validation cannot pass after remediation
- Operator capacity insufficient for safe oversight

### Deliverables on exit

- [ ] Completed validation run report (`validation_run_template.md`)
- [ ] Daily metrics export
- [ ] Incident log (if any)
- [ ] Updated `trl_assessment_report.md` with pilot outcome
- [ ] Go/no-go decision for TRL 7 preparation

---

## Related commands

```bash
# Readiness
curl -H "Authorization: Bearer $TOKEN" \
  "$API/api/v1/shops/$SHOP_ID/pilot-readiness"

# Enable pilot (admin)
curl -X PUT -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"pilot_enabled": true, "max_auto_sent_messages_per_day": 50, "max_auto_created_orders_per_day": 20}' \
  "$API/api/v1/shops/$SHOP_ID/pilot-settings"

# Emergency stop
curl -X POST -H "Authorization: Bearer $TOKEN" \
  "$API/api/v1/shops/$SHOP_ID/pilot/emergency-stop"
```
