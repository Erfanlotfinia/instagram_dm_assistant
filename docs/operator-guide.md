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


## Fashion order operator guide

### Mapping posts
Use **Post Mapping** to connect one Instagram post URL to one or more products. Multi-product posts are supported by adding multiple mappings with the same normalized post URL and optional admin labels/display order.

### Managing variants
Add variants with raw colors and sizes. The backend stores normalized color/size fields so Persian names, English names, informal spellings, numeric sizes, free-size phrases, shoe sizes, and category size charts can resolve consistently.

### Testing in the DM Simulator
Open **DM Simulator**, choose an Instagram account, enter a fake customer message and optional shared post URL, then run. The simulator creates a test conversation marked `is_simulation=true`, runs the same orchestrator, shows intent, slots, product/variant resolution, inventory, next state, suggested reply, and preview/handoff decision, but never sends real Instagram messages.

### Approving low-confidence replies
When confidence is below the shop auto-send threshold or preview mode is enabled, the conversation stores `suggested_outbound` and `preview_required=true`. Operators can edit and send the reply from the conversation detail page.

### Taking over conversations
Use **Take over** to pause the agent and route the conversation to an operator. Use **Release to agent** only after the ambiguity, complaint, payment issue, high-value risk, or variant mismatch has been resolved.

### Reviewing failed jobs
Use the failed job viewer endpoint `GET /api/v1/jobs/failed` to inspect retry/DLQ payloads and error messages. RabbitMQ declares a main queue, retry queue, and DLQ with max retry settings.
