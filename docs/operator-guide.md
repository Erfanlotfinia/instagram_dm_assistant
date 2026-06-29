# Operator Guide

Screen-focused workflows for the Modira admin UI. See [ui-design-guide.md](./ui-design-guide.md) for full IA and [api-documentation.md](./api-documentation.md) for endpoints.

## Daily workflow

1. Sign in → select shop (top bar).
2. **Overview** — scan handoffs, unpaid orders, failed jobs.
3. **Handoffs** (sidebar badge) — triage escalated threads by priority and wait time.
4. **Inbox** — filter `assigned_to_me`, `waiting_for_payment`, or search by customer/order.
5. Take over → reply or approve suggested reply → release to agent or mark resolved.
6. **Orders** — confirm shipments after payment.

## Inbox & handoffs

| Action | When | API |
|--------|------|-----|
| **Take over** | Low confidence, complaint, payment issue, repeated agent failure | `POST .../take-over` |
| **Send message** | After take-over; manual outbound | `POST .../messages` |
| **Approve suggested reply** | `preview_required` on conversation | Suggested replies API |
| **Release to agent** | Issue resolved | `POST .../release-to-agent` |
| **Mark resolved** | Thread complete | `POST .../mark-resolved` |
| **Assign** | Route to another operator | `POST .../assign` |

**Filters to use:** urgent, high priority, handoff, waiting for payment, ready to order, low confidence, simulation, needs attention, search (name, phone, IG id, order id, product).

## Orders

| Action | When |
|--------|------|
| **Mark paid** | Bank transfer / cash outside gateway |
| **Ship** | After payment; add tracking |
| **Cancel** | Unpaid; releases reservation |
| **Send payment link** | Customer ready to pay |

Order timeline states: draft → clarification → confirm → reserve → payment → paid → complete. See [order-correctness-architecture.md](./order-correctness-architecture.md).

## Fashion / catalog tips

- **Mapping** (`/catalog/mapping`) — link Instagram post URLs to products; multi-product posts supported.
- **Attributes** — Persian/English color and size aliases improve variant resolution.
- **DM Simulator** (`/automation/simulator`) — test messages without sending real DMs; look for `is_simulation` badge.
- **Demand** (`/analytics/demand`) — review unavailable requests and fix catalog gaps.

## Escalation

1. Check post mapping and variant stock.
2. Open **Intelligence** on conversation for decision trace.
3. Escalate to admin if channels/webhooks are down (**System → Health**, **Channels**).

## Audit

Operator actions write to `admin_audit_logs` and conversation events.
