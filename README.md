# Modira — AI Social Media Admin OS

Modira is an AI Social Media Admin OS that automates sales, support, and customer communication across all social channels. It is built for online shops that need one automation-first operating layer for Instagram, WhatsApp, Telegram, Bale, and Rubika.

## Product philosophy

```text
Automation First → LLM Fallback → Human Handoff
```

Deterministic rules and business services own prices, stock, order state, payments, shipping, and policy enforcement. LLM fallback is isolated to ambiguity resolution and safe drafting; it must not set prices, set stock, finalize orders, or bypass business rules.

## Architecture

```text
InstagramAdapter ┐
WhatsAppAdapter  ├──> NormalizedMessage
TelegramAdapter  ┤        channel, user_id, conversation_id,
BaleAdapter      ┤        message_type, content, attachments, metadata
RubikaAdapter    ┘
                       │
                       ▼
Unified Inbox / Message Event System
                       │
                       ▼
Core Engine
  ├─ ConversationContextGraph / ConversationContextService
  ├─ AutomationEngine + AutomationHandlerRegistry
  ├─ CatalogQueryPlanner + ProductDiscoveryService + CatalogService
  ├─ ScenarioRouter
  ├─ OrderService / PaymentService / ShippingService
  ├─ LLMFallbackOrchestrator
  └─ HumanHandoffService
                       │
                       ▼
Admin dashboard, analytics, scenario simulator, and operator controls
```

## Generic product model

Modira treats catalog items generically so shops can sell electronics, tools, cosmetics, furniture, services, digital products, or any other product category:

- `product_id`
- `title`
- `description`
- `category`
- `attributes` (key-value)
- `variants`
- `price`
- `stock`
- `media`
- `availability_rules`

Legacy catalog fields are adapted into this generic model by `ProductDiscoveryService` while preserving existing order and payment infrastructure.

## Local development

```bash
cp .env.example .env
docker compose up --build
```

Backend checks:

```bash
cd backend
pytest
ruff check .
```

Frontend checks:

```bash
cd frontend
npm run typecheck
npm run lint
npm test
npm run build
```

## Key directories

- `backend/app/channels/` — channel adapter layer for supported social providers.
- `backend/app/schemas/channels.py` — normalized inbound/outbound schemas and the Modira `NormalizedMessage` envelope.
- `backend/app/services/social_admin/` — channel-agnostic core engine modules.
- `backend/app/services/order_service.py`, `payment_service.py`, `shipping_service.py` — business-rule-owned commerce state transitions.
- `frontend/src/` — Modira admin dashboard, analytics, simulator, and controls.
