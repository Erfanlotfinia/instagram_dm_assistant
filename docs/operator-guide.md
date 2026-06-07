# Operator Guide

Operators handle day-to-day conversation and order management in the admin UI.

## Daily workflow

1. Sign in and select your shop.
2. Check **Dashboard** for handoffs and unpaid orders.
3. Open **Conversations** filtered by `Pending handoff`.
4. Take over when the agent escalates; reply manually if needed.
5. Release back to agent when the issue is resolved.
6. Monitor **Orders** for `waiting_for_payment` and confirm shipments after payment.

## Handoff procedures

| Action | When to use |
|--------|-------------|
| **Take over** | Customer needs human help, low confidence, or repeated agent failures |
| **Send message** | Only after take-over; sends Instagram reply |
| **Release to agent** | Issue resolved; resume automated flow |
| **Mark resolved** | Conversation complete; closes thread |

## Order operations

- **Mark paid** — customer paid outside mock gateway (bank transfer, cash)
- **Ship** — add tracking code after payment
- **Cancel** — release reserved inventory for unpaid orders

All operator actions are recorded in `admin_audit_logs`.

## Escalation

If the agent repeatedly fails:

1. Check product mapping for the Instagram post URL.
2. Verify variant stock in **Products**.
3. Review conversation slots in conversation detail.
4. Contact admin if Instagram token or webhook is disconnected.
