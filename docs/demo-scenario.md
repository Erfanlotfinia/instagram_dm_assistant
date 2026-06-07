# Demo Scenario: Persian Instagram Order Flow

This walkthrough demonstrates the full pilot flow after seeding and starting the stack.

## Setup

```bash
cp .env.example .env
docker compose up --build
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.scripts.seed
```

Sign in with seeded admin credentials from `app/scripts/seed.py`.

## Scenario steps

| Step | Actor | Action | Expected result |
|------|-------|--------|-----------------|
| 1 | Customer | Sends Instagram post share + text `مشکی سایز L` | Webhook ingests message; job queued |
| 2 | Agent | Resolves product from post URL mapping | Slots updated with product + variant |
| 3 | Agent | Detects missing customer info | Outbound asks for name, phone, address |
| 4 | Customer | Sends complete info | Slots merged; draft order created |
| 5 | Customer | Confirms order (`بله تأیید می‌کنم`) | Order → `waiting_for_payment`; payment link sent |
| 6 | Customer | Pays via mock link `/api/v1/payments/mock/pay/{id}` | Order → `paid`; confirmation DM sent |
| 7 | Admin | Opens Orders in admin UI | Paid order visible with timeline |

## Automated test coverage

The same flow is covered by:

- `backend/app/tests/test_sprint7_e2e.py::test_e2e_inbound_to_paid_order`
- `backend/app/tests/test_order_agent_flow.py`

## Sample webhook payloads

```python
# backend/app/tests/fixtures/instagram_webhook.py
SAMPLE_SHARED_POST_PAYLOAD   # Instagram post share
SAMPLE_INSTAGRAM_MESSAGE_PAYLOAD  # Text message
```

## Failure scenarios tested

- Invalid LLM JSON response
- Product not found for unknown post URL
- Stock unavailable on confirmation
- Duplicate webhook `instagram_message_id`
- Duplicate payment callback reference
