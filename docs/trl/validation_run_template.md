# TRL Validation Run Report

> Copy this template for each formal TRL validation execution.  
> Do not fabricate results — mark fields **MISSING** when not measured.

---

## Run metadata

| Field | Value |
|-------|-------|
| **Run ID** | `{uuid}` |
| **Date (UTC)** | `{YYYY-MM-DD HH:MM}` |
| **Environment** | `local` / `docker-compose` / `staging` / **MISSING** |
| **Commit hash** | `{git rev-parse HEAD}` |
| **Dataset version** | `trl_scenarios.json` @ `{commit or tag}` |
| **Shop** | `trl-fashion-demo` (`seed_trl_demo_data`) |
| **Scenario limit** | `100` (full) / `{N}` (partial) |
| **LLM mode** | `rule-based` (default TRL runner) / `openai-live` / **MISSING** |
| **Executed by** | `{name}` |

---

## Summary

| Metric | Value |
|--------|-------|
| **Total scenarios** | `{N}` |
| **Passed** | `{N}` |
| **Failed** | `{N}` |
| **Pass rate** | `{passed/total}` |
| **Run status** | `completed` / `failed` |
| **All thresholds passed** | `yes` / `no` / **MISSING** |
| **Average processing time (ms)** | `{value}` |
| **P95 processing time (ms)** | `{value}` |

---

## Failed scenarios

| Scenario ID | Category | Failure reasons | Conversation ID |
|-------------|----------|-----------------|-----------------|
| `{TRL-XXX}` | `{category}` | `{reason}` | `{uuid or —}` |

*If none: "No failed scenarios."*

---

## Metrics

| Metric | Result | Threshold | Pass |
|--------|--------|-----------|:----:|
| intent_accuracy | | ≥ 0.90 | |
| slot_extraction_accuracy | | ≥ 0.85 | |
| product_resolution_accuracy | | ≥ 0.90 | |
| variant_resolution_accuracy | | ≥ 0.85 | |
| false_order_creation_count | | ≤ 0 | |
| false_payment_status_change_count | | ≤ 0 | |
| inventory_double_reservation_count | | ≤ 0 | |
| invalid_llm_json_handled_rate | | = 1.0 | |
| duplicate_webhook_idempotency_rate | | = 1.0 | |
| critical_security_tests_pass_rate | | = 1.0 | |

### Additional metrics (informational)

| Metric | Value |
|--------|-------|
| order_creation_success_rate | |
| handoff_precision | |
| handoff_recall | |
| false_auto_send_count | |
| average_risk_score | |
| critical_risk_count | |
| scenario_pass_rate_by_category | `{json}` |

---

## Threshold comparison

```
thresholds_passed: {
  "intent_accuracy": true/false,
  ...
}
```

**Overall TRL 5 threshold gate:** `{PASS / FAIL / NOT RUN}`

### Caveats for this run

- [ ] Rule-based LLM substitute used (default) — does not validate OpenAI extraction
- [ ] Stubbed metrics (payment, inventory double-reserve, idempotency, security) — verify separately
- [ ] Partial scenario limit used — not full 100-scenario gate

---

## Commands used

```bash
# Seed TRL demo data
docker compose exec backend python -m app.scripts.seed_trl_demo_data

# Run validation (API)
curl -X POST -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"reset_demo_data": false}' \
  http://localhost:8000/api/v1/shops/<shop_id>/trl-validation/run

# Or export summary script
docker compose exec backend python -m app.scripts.generate_trl_report
```

---

## Sign-off

| Role | Name | Date | Decision |
|------|------|------|----------|
| Engineering lead | | | TRL 5 gate: Pass / Fail / Deferred |
| Product owner | | | Accept residual risk: Yes / No |
| Operations | | | Environment suitable: Yes / No |

**Comments:**

---

## Attachments

- [ ] Exported `generate_trl_report` markdown
- [ ] Failed scenario JSON export
- [ ] Backend test log (`pytest`) from same commit
- [ ] Docker Compose `ps` / health check snapshot
