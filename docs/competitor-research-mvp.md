# Competitor-informed MVP extensions

## Positioning

This product is **not a generic chatbot**. It is an Instagram-first, channel-independent fashion order agent that turns DMs, comments, story replies, reels, and ad comments into accurate, payable, shippable orders.

The core order pipeline consumes normalized channel messages (`InboundMessage`, `OutboundMessage`, `ChannelConversation`, and `ChannelCustomerIdentity`) so Instagram remains the first-class channel while WhatsApp, Telegram, and Web Chat can be added without hardcoding provider payloads into order logic.

## Competitor differentiation

- **Meta Business Agent:** we specialize below the generic assistant layer: Instagram post-to-product mapping, SKU/variant validation, inventory reservation, payment safety, and shipment workflow.
- **Manychat / Inrō:** we add comment-to-DM growth automation, then continue into deterministic fashion ordering instead of stopping at lead capture.
- **Chatfuel:** we keep setup fast, but encode fashion-specific business rules instead of relying on no-code chatbot flows alone.
- **Gorgias:** we add agent decision traces, a DM simulator, and product/variant reasoning designed for Instagram fashion DMs.
- **SleekFlow / Respond.io / Tidio:** we include analytics and handoff, but optimize metrics around post conversion, unavailable demand, paid orders, and fashion variant resolution.

## Demo scenario

Customer shares an Instagram post and writes:

> مشکی سایز L یک عدد

Expected flow:

1. The Instagram provider stores the raw payload and normalizes it to `InboundMessage`.
2. The post resolver maps the shared post to one or more products. If multiple products are mapped, the agent asks the customer which item they mean.
3. The LLM extracts raw slots only: raw color `مشکی`, raw size `L`, quantity `1`.
4. Backend normalization maps `مشکی` to `black` and `L` to `L`.
5. `VariantResolver` deterministically selects an in-stock variant or returns alternatives and logs unavailable demand.
6. Inventory is checked before any draft order is created.
7. Missing name, phone, city, address, and postal code are requested.
8. A draft order is created and confirmation is requested.
9. A payment link is generated only after explicit confirmation.
10. Payment callback idempotently marks the order paid.
11. Admin reviews the full decision trace in the conversation detail/simulator.

## Operator guide

1. Create products and variants with normalized colors and sizes.
2. Map Instagram posts to one or more products; use display order, visual hints, caption hints, and primary flags for multi-product posts.
3. Configure color aliases, size aliases, and size charts under Fashion endpoints/UI.
4. Create trigger rules for keywords such as `price`, `link`, `موجوده`, and `قیمت`.
5. Run the DM Simulator before enabling automations.
6. Configure Agent Studio preview rules, brand voice, selling style, discount policy, and handoff policy.
7. Approve low-confidence previews and high-value orders before sending.
8. Handle human handoff from the omnichannel conversation queue.
9. Review analytics: funnel, posts, unavailable demand, handoff, and response time.
10. Review failed jobs, readiness checks, and audit logs before scaling.

## New local commands

```bash
cd backend && alembic upgrade head
cd backend && pytest
cd frontend && npm test -- --runInBand
cd frontend && npm run build
```
