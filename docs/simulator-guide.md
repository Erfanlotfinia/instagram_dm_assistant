# DM Simulator Guide

The DM simulator creates simulated conversations and messages, then runs the same `ConversationOrchestrator` used by real inbound Instagram messages.

## Rules

- Simulator conversations and messages are marked `is_simulation=true`.
- The orchestrator does not send real Instagram messages for simulation conversations.
- Reset removes only simulation conversations for the selected shop.

## Suggested validation

1. Seed demo data.
2. Open **DM Simulator**.
3. Send shared-post and text-only scenarios.
4. Verify intent, extracted slots, product resolution, variant resolution, inventory result, next state, suggested reply, and decision trace.
5. Reset simulation data and confirm non-simulation data remains.
