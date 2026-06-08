# Sprint C — Smart Operator Inbox

Sprint C makes the admin panel useful for daily fashion-order operations: prioritized conversation queue, operator timeline, one-click actions, and a split-pane detail layout.

## Features

### Smart Conversation Queue
- `priority_score`, `priority_level` (urgent/high/medium/low), `priority_reason`, `needs_attention`, `last_operator_action_at`
- `ConversationPriorityService` recalculates after messages, agent runs, order changes, and handoff events
- List sorted by priority score, then last message time
- Filters: urgent, high priority, handoff, waiting for payment, ready to order, low confidence, assigned to me, unassigned, needs attention, simulation/real
- Search: customer name, phone, Instagram ID, order ID, product title

### Conversation Timeline
- `conversation_events` table with typed events for messages, replies, orders, payments, handoffs, and operator actions
- Events exposed on conversation detail API

### One-click Operator Actions
- Conversation: take-over, release-agent, send-manual-message, assign
- Order: send-payment-link, mark-paid, send-tracking-code, cancel
- All mutating actions write audit logs and conversation events where relevant

### Admin UI
- Smart inbox list with priority badges and commerce columns
- Split operator layout: thread + manual input + suggested reply (left), customer/order context + quick actions (right)
- Customer profile panel with order history, preferences, and inline edit

## Migrations

- `backend/app/db/migrations/versions/20260608_0012_sprint_c_smart_inbox.py`

## Backend endpoints

| Method | Path |
|--------|------|
| GET | `/api/v1/shops/{shop_id}/conversations` (extended filters) |
| GET | `/api/v1/shops/{shop_id}/conversations/{conversation_id}` (events, profile, inventory) |
| POST | `/api/v1/shops/{shop_id}/conversations/{conversation_id}/assign` |
| POST | `/api/v1/shops/{shop_id}/conversations/{conversation_id}/send-manual-message` |
| POST | `/api/v1/shops/{shop_id}/conversations/{conversation_id}/release-agent` |
| GET/PATCH | `/api/v1/shops/{shop_id}/customers/{customer_id}` |
| POST | `/api/v1/shops/{shop_id}/orders/{order_id}/send-payment-link` |
| POST | `/api/v1/shops/{shop_id}/orders/{order_id}/send-tracking-code` |

Existing endpoints (`take-over`, `mark-paid`, `cancel`, etc.) remain backward compatible.

## Frontend

- `frontend/src/pages/ConversationsPage.tsx`
- `frontend/src/pages/ConversationDetailPage.tsx`
- `frontend/src/components/conversations/*`
- `frontend/src/types/conversation.ts`
- `frontend/src/services/apiClient.ts`

## Tests

Backend:
- `backend/app/tests/test_sprint_c_priority.py`
- `backend/app/tests/test_sprint_c_operator_actions.py`

Frontend:
- `frontend/src/pages/ConversationsPage.test.tsx`
- `frontend/src/pages/ConversationDetailPage.test.tsx`
- `frontend/src/components/conversations/PriorityBadge.test.tsx`

## Run locally

```bash
cp .env.example .env
docker compose up --build
```

Apply migrations (automatic on backend startup) or manually:

```bash
docker compose exec backend alembic upgrade head
```

Backend tests:

```bash
docker compose exec backend pytest app/tests/test_sprint_c_priority.py app/tests/test_sprint_c_operator_actions.py -q
```

Frontend tests:

```bash
cd frontend && npm test
```

Admin UI: http://localhost:5173 — open **Conversations** after selecting a shop.

## Remaining risks / TODOs

- Priority weights are heuristic; tune per shop vertical with analytics feedback
- `assigned_to_me` requires authenticated operator context on list API
- Conversation search joins orders/products — add DB indexes if inbox grows large
- Tracking-code dialog is minimal; richer shipment provider selection can follow Sprint D
- Real-time inbox refresh (WebSocket/SSE) not included; operators rely on manual refresh today
