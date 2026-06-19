# Modira Enterprise Admin OS

Modira is a multi-channel Enterprise Admin OS for commerce operators. It centralizes inbound customer messages, catalog-aware automation, human handoff, analytics, and system operations across Instagram, WhatsApp, Telegram, Bale, and Rubika.

## Channel architecture

All providers use the same adapter contract: verify the webhook, normalize provider payloads into a generic message-received event, enqueue `channel.message.received`, run automation-first execution, and send outbound replies through the provider adapter. The canonical webhook route is `/api/v1/channels/{provider}/webhook`.

## Credentials and secrets

Provider access tokens are shop-specific channel credentials. They are encrypted at rest with `TOKEN_ENCRYPTION_KEY`, are never returned by API responses, and must be redacted from logs, job payloads, and errors. Global Meta application credentials (`META_APP_ID`, `META_APP_SECRET`, graph API settings) identify the shared Meta app and validate signatures; they are not shop page tokens.

Production must set a strong `TOKEN_ENCRYPTION_KEY`, keep `WEBHOOK_SIGNATURE_BYPASS=false`, restrict `CORS_ORIGINS`, and avoid frontend provider-token variables. Frontend env may contain browser-safe URLs such as `VITE_API_BASE_URL` only.

## Execution model

Automation rules, deterministic catalog resolution, order state transitions, and policy gates run before any model fallback. LLM fallback is bounded to extraction, classification, or drafting when deterministic logic cannot resolve safely. Risky, ambiguous, policy-sensitive, or customer-impacting actions require preview or human handoff.

## Catalog model

Catalog attributes are generic key/value facts scoped by shop, category, and aliases. Clothing color and size are supported as ordinary attributes rather than product-wide architecture assumptions.
