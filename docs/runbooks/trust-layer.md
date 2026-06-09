# Trust Layer Runbook

## Emergency stop

1. Open **Pilot Control Center** (`/pilot-control`) or **Pilot Readiness** (`/pilot-readiness`).
2. Review scope preview: active non-simulation conversations affected.
3. Activate emergency stop with a reason. This:
   - Sets `emergency_stop_enabled` on pilot settings
   - Blocks auto-send and order side-effects in the orchestrator immediately
   - Opens a critical incident with timeline events
4. Verify: no new auto-sent messages or draft orders for live conversations.
5. Resume via **Pilot Readiness → Resume pilot** when root cause is resolved.

## Replay certification (pre-production)

1. Open **DM Simulator → Deterministic replay**.
2. Run the golden replay pack (or CI: `python -m app.scripts.run_golden_replay_suite`).
3. Confirm pass rate is 100% for golden scenarios.
4. Inspect failed items: open **Trace** drawer for policy checks, confidence bands, blocked actions.
5. Do not promote model/prompt/policy versions until golden pack passes on frozen catalog snapshot.

## Pilot operating modes

| Mode | Behavior |
|------|----------|
| Shadow | Suggestions only; `no_state_change_in_shadow_mode` blocks writes |
| Copilot | Operator approval required for writes |
| Autonomous low-risk | Writes only when all enabled policies pass |

Change mode in **Pilot Control Center**. All changes are recorded in `pilot_mode_history` and pilot event log.

## Incident timeline

- List: `/incidents`
- Detail: `/incidents/{id}` — shows who changed what, mode changes, affected conversations
- Emergency stops auto-create incidents with `trigger=emergency_stop`

## Structured logs

All replay and trace operations emit `trace_id` and `request_id` in structured logs. Use these IDs to correlate API requests, `trace_events`, and `simulator_run_items`.
