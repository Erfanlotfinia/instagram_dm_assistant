# TRL 6 Pilot Test Script — Modira

## Purpose

This script prepares and executes a constrained TRL 6 pilot for an AI Social Media Admin OS in realistic shop operations. The pilot validates production-like traffic, operator handoff, order creation, payment flow, monitoring, and rollback under real operational constraints.

## Pre-pilot checklist

- Confirm Instagram webhook subscription is connected for the pilot account.
- Run the latest TRL validation suite and verify all acceptance thresholds pass.
- Remove demo data from the shop or isolate it with simulation flags.
- Configure real products, variants, prices, SKU snapshots, and Instagram post mappings.
- Verify inventory within 24 hours of pilot start.
- Configure payment mode and callback handling.
- Assign at least one owner/admin/operator for the pilot window.
- Configure handoff policy, escalation reasons, and support contact.
- Enable pilot mode with conservative daily limits.
- Test emergency stop and resume before admitting real customer traffic.
- Review `/api/v1/shops/{shop_id}/pilot-readiness` and resolve all blocking criteria.

## Test data requirements

- At least 10 active real products with accurate images/captions.
- At least 80% of active products mapped to Instagram product/post identifiers, or the configured pilot threshold.
- Each pilot product has active variants with color, size, SKU, price, and stock quantity.
- Test customer conversations covering new customer, returning customer, out-of-stock, unclear variant, cancellation, payment success, and payment failure.
- Pilot Instagram account IDs and optional allowed product IDs listed in pilot settings.

## Operator roles

- **Pilot owner:** decides go/no-go, owns daily review, approves rollback.
- **Primary operator:** monitors inbox, approves previews, handles high-risk handoffs.
- **Backup operator:** covers breaks and incident response.
- **Technical on-call:** monitors failed jobs, readiness, payments, webhooks, and logs.

## Test scenarios

1. **Simple order flow:** Customer asks for an allowed product and valid variant; agent progresses only within pilot limits.
2. **First 50 orders approval:** Confirm early orders are previewed or held for operator approval.
3. **Daily auto-send cap:** Seed traffic until the cap is reached; verify auto-send is disabled and an event is logged.
4. **Daily auto-order cap:** Create eligible order traffic until cap is reached; verify progression is blocked and logged.
5. **Selected product pilot:** Customer asks for a non-allowed product; verify preview/handoff instead of order progression.
6. **Human handoff:** Customer sends complaint, payment issue, address ambiguity, or high-risk content; verify operator takeover.
7. **Payment callback failure:** Simulate failed/cancelled payment callback; verify event log and metrics reflect it.
8. **Failed worker job:** Simulate failed job; verify metrics, event log, warning banner, and readiness failure.
9. **Emergency stop:** Activate emergency stop during traffic; verify no auto-send or order progression occurs.
10. **Resume:** Resume pilot after stop; verify automation only returns within configured limits.

## Success criteria

- No critical unresolved failed jobs.
- `/ready` returns `ok` during the pilot window.
- Latest TRL validation thresholds pass before start.
- Zero unauthorized Instagram accounts or products enter automation.
- Auto-send and auto-order caps block automation at configured limits.
- Emergency stop takes effect immediately and is visible in UI/API.
- Operators can take over and release conversations safely.
- Payment failures are logged and reviewed.
- Daily metrics and event logs are complete enough for pilot review.

## Rollback plan

1. Press **Emergency stop** on the Pilot Readiness page or call `POST /api/v1/shops/{shop_id}/pilot/emergency-stop`.
2. Disable pilot mode in pilot settings if a prolonged pause is required.
3. Switch Agent Studio to copilot or human-first mode.
4. Assign all open pilot conversations to operators.
5. Pause webhook worker consumption if duplicate or unsafe processing continues.
6. Resolve failed jobs manually; do not bulk retry until root cause is known.
7. Communicate customer-impacting delays using approved templates.

## Incident handling

- Classify severity: info, warning, error, or critical.
- For critical incidents, activate emergency stop first, then investigate.
- Capture affected conversation IDs, order IDs, payment IDs, failed job IDs, and pilot event IDs.
- Record root cause, customer impact, mitigation, and prevention action.
- Resume only after readiness criteria are restored and pilot owner approves.

## Daily pilot review checklist

- Review readiness criteria and warning banners.
- Review pilot metrics: inbound messages, auto-sends, previews, handoffs, orders, payments, failed jobs, invalid LLM outputs, response times, and takeovers.
- Review all warning/error/critical pilot events.
- Confirm inventory freshness and product mapping coverage.
- Confirm operators are assigned for the next pilot window.
- Adjust daily caps only after reviewing incidents and false automation.
- Decide continue, pause, expand, or rollback.

## How to run the readiness check

```bash
curl -H "Authorization: Bearer <token>" \
  "https://<host>/api/v1/shops/<shop_id>/pilot-readiness"
```

The shop is TRL 6 pilot-ready only when `ready_for_trl6_pilot` is `true` and no warning banners indicate emergency stop, failed jobs, or outdated validation.
