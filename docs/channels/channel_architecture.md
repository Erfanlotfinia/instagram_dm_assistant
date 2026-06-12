# Channel architecture

The Fashion Order OS now treats messaging channels as adapters around one commerce engine. Instagram, WhatsApp Cloud API, Telegram Bot API, Bale Bot API and Rubika Bot API normalize inbound provider payloads into `NormalizedInboundMessage` and send outbound replies through `NormalizedOutboundMessage`.

## Flow

1. Provider webhook reaches `/api/v1/channels/{provider}/webhook` or a compatibility `/api/v1/webhooks/{provider}` endpoint.
2. `ChannelProviderAdapter` verifies webhook security and parses the payload.
3. `ChannelWebhookIngestionService` creates/updates channel contact identities, customers, channel conversations, channel messages and internal messages.
4. An outbox event is committed before async workers publish jobs.
5. `ChannelOutboundService` applies channel policy and sends through a provider adapter.

No provider should own order creation, inventory reservation, payment safety or LLM orchestration logic.
