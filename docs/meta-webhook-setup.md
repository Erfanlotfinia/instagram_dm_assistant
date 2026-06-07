# Meta Instagram Webhook Setup

## 1. Create Meta app

1. Go to [Meta for Developers](https://developers.facebook.com/).
2. Create a Business app with **Instagram** product.
3. Connect your Instagram professional account and Facebook Page.

## 2. Configure webhook

| Field | Value |
|-------|-------|
| Callback URL | `https://<your-api-host>/api/v1/webhooks/instagram` |
| Verify token | Same as `INSTAGRAM_WEBHOOK_VERIFY_TOKEN` |
| App secret | Set as `INSTAGRAM_APP_SECRET` for signature verification |

Subscribe to messaging fields your pilot needs (typically `messages`).

## 3. Verification flow

Meta sends:

```http
GET /api/v1/webhooks/instagram?hub.mode=subscribe&hub.verify_token=...&hub.challenge=...
```

The API returns `hub.challenge` when the verify token matches.

## 4. Inbound events

Meta POSTs JSON payloads. When `INSTAGRAM_APP_SECRET` is set, the API validates `X-Hub-Signature-256`.

Processing pipeline:

1. Store raw payload in `webhook_events`
2. Resolve `instagram_accounts` by recipient `ig_user_id`
3. Deduplicate by `instagram_message_id`
4. Persist customer, conversation, message
5. Publish job to RabbitMQ `instagram.message.received`
6. Worker runs agent orchestration under Redis conversation lock

## 5. Local testing with ngrok

```bash
docker compose up --build
ngrok http 8000
```

Use the ngrok HTTPS URL as the Meta callback URL.

## Sample payload

See `backend/app/tests/fixtures/instagram_webhook.py` for `SAMPLE_INSTAGRAM_MESSAGE_PAYLOAD` and `SAMPLE_SHARED_POST_PAYLOAD`.
