# Demo Scenario: Persian Instagram Order Flow

This walkthrough demonstrates the full pilot flow after seeding and starting the stack.

## Setup

```bash
cp .env.example .env
docker compose up --build
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.scripts.seed
```

Sign in with `admin@example.com` / `changeme123`. The seed creates the demo shop, Instagram account `17841400000000001`, product mapping `https://www.instagram.com/p/ABC123/`, and a black size L variant with stock.

## Scenario steps

| Step | Actor | Action | Expected result |
|------|-------|--------|-----------------|
| 1 | Customer | Sends Instagram post share + text `مشکی سایز L یک عدد` | Webhook ingests message; job queued |
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


## Competitive fashion demo scenario

Customer message: `این کارو مشکی سایز L می‌خوام`

Expected specialized fashion flow:

1. The shared Instagram post URL is resolved through post-to-product mappings; if the post has multiple products, the agent asks which item the customer means and stores the selection in conversation slots.
2. Raw color `مشکی` is normalized to canonical `black`, separate from the raw customer text.
3. Raw size `L` is normalized to canonical `L`; numeric, free-size, shoe, and category size charts are resolved deterministically.
4. The backend `VariantResolver` selects and validates the SKU. The LLM never chooses price, inventory, SKU, payment state, or shipment state directly.
5. Inventory is checked against available stock and alternatives are suggested for mismatches or unavailable demand.
6. Missing customer information is requested before creating a draft order.
7. The order is not finalized until explicit customer confirmation.
8. A payment link is generated only after confirmation; idempotent callbacks mark the order paid once.
9. Operators can see normalized slots, product candidates, variant alternatives, confidence, suggested reply, handoff state, and the audit trail.
