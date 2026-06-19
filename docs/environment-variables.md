# Environment Variables

Modira separates platform configuration from shop-specific provider credentials.

## Platform variables

| Variable | Purpose |
| --- | --- |
| `APP_ENV` | Runtime environment; production enables strict secret checks. |
| `DATABASE_URL`, `REDIS_URL`, `RABBITMQ_URL`, `QDRANT_URL` | Data, lock, queue, and vector services. |
| `JWT_SECRET_KEY` | Admin auth signing secret. |
| `TOKEN_ENCRYPTION_KEY` | Required in production; encrypts per-shop channel credentials. |
| `WEBHOOK_INTERNAL_SECRET` | Internal verification secret for provider challenge flows where applicable. |
| `META_APP_ID`, `META_APP_SECRET`, `META_GRAPH_API_VERSION`, `META_GRAPH_API_BASE_URL` | Global Meta app configuration and signature validation. These are not shop page tokens. |
| `WEBHOOK_SIGNATURE_BYPASS` | Must be `false` in production. |
| `ENABLED_CHANNEL_PROVIDERS` | Enabled adapters, for example `instagram,whatsapp,telegram,bale,rubika`. |
| `ENABLE_REAL_PROVIDER_SEND` | Enables real provider outbound adapter calls. |
| `RABBITMQ_QUEUE_MESSAGE_RECEIVED` | Generic inbound queue, normally `channel.message.received`. |
| `LLM_PROVIDER`, `LLM_MODE`, model/API-key variables | Bounded LLM extraction and drafting. |
| `VITE_API_BASE_URL` | Browser-safe frontend API URL. Never put provider tokens in frontend env. |

## Shop credentials

Shop-specific provider tokens, bot tokens, phone IDs, account IDs, webhook secrets, and send identities are stored on channel accounts. APIs return metadata/status only and never raw decrypted tokens.
