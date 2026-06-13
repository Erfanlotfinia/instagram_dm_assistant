# Environment Variables Guide

## Core

| Variable | Description | Example |
|----------|-------------|---------|
| `APP_ENV` | Runtime environment | `production` |
| `LOG_LEVEL` | Python log level | `INFO` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+psycopg://...` |
| `REDIS_URL` | Redis for locks and rate limits | `redis://redis:6379/0` |
| `RABBITMQ_URL` | AMQP broker | `amqp://guest:guest@rabbitmq:5672/` |
| `QDRANT_URL` | Vector DB HTTP endpoint | `http://qdrant:6333` |

## Security

| Variable | Description |
|----------|-------------|
| `JWT_SECRET_KEY` | HS256 signing key (min 16 chars) |
| `TOKEN_ENCRYPTION_KEY` | Fernet key for Instagram tokens (min 32 chars) |
| `CORS_ORIGINS` | JSON list of allowed admin origins |
| `INSTAGRAM_APP_SECRET` | Meta app secret; enables webhook signature check |
| `RATE_LIMIT_ENABLED` | Enable Redis rate limiting |
| `RATE_LIMIT_LOGIN_PER_MINUTE` | Login attempts per IP per minute |
| `RATE_LIMIT_WEBHOOK_PER_MINUTE` | Webhook POSTs per IP per minute |
| `RATE_LIMIT_OUTBOUND_MESSAGE_PER_MINUTE` | Manual outbound messages per IP per minute |

## Instagram / Meta

| Variable | Description |
|----------|-------------|
| `INSTAGRAM_WEBHOOK_VERIFY_TOKEN` | Meta webhook verification token |
| `ENABLE_REAL_INSTAGRAM_SEND` | `true` to call Graph API; `false` for local mock send |

## Agent / LLM

| Variable | Description |
|----------|-------------|
| `LLM_PROVIDER` | `openai` (default) or `gemini` |
| `LLM_MODE` | `mock` for tests/local without API calls; `live` for real extraction |
| `OPENAI_API_KEY` | OpenAI-compatible API key (AvalAI or OpenAI) when `LLM_PROVIDER=openai` |
| `OPENAI_API_BASE_URL` | OpenAI-compatible API base URL (default: `https://api.avalai.ir/v1`) |
| `OPENAI_MODEL` | Chat model when using OpenAI provider |
| `OPENAI_EMBEDDING_MODEL` | Embedding model when using OpenAI provider |
| `GEMINI_API_KEY` | Google Gemini API key when `LLM_PROVIDER=gemini` |
| `GEMINI_MODEL` | Gemini chat model (default: `gemini-2.5-flash`) |
| `GEMINI_EMBEDDING_MODEL` | Gemini embedding model (default: `gemini-embedding-001`, 3072-dim) |

When switching `LLM_PROVIDER`, re-run catalog semantic reindex because embedding vector sizes may differ.

## Queue / workers

| Variable | Description |
|----------|-------------|
| `RABBITMQ_MAX_RETRIES` | Max processing retries before DLQ |
| `RABBITMQ_RETRY_DELAY_MS` | Retry queue TTL delay |
| `CONVERSATION_LOCK_TTL_SECONDS` | Redis lock TTL per conversation |
| `BACKGROUND_JOB_INTERVAL_SECONDS` | Scheduler cycle interval |
| `EMBEDDING_REFRESH_BATCH_SIZE` | Products re-indexed per scheduler run |
| `ORDER_EXPIRATION_MINUTES` | Unpaid order TTL |

## Frontend

| Variable | Description |
|----------|-------------|
| `VITE_API_BASE_URL` | Backend URL visible to browser |
