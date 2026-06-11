# Security Configuration

See also [environment-variables.md](environment-variables.md) and [meta-webhook-setup.md](meta-webhook-setup.md).

## Required production/staging variables

- `APP_ENV=production` or `staging`
- `JWT_SECRET_KEY` — 32+ characters, non-default
- `TOKEN_ENCRYPTION_KEY` — 32+ characters, non-default
- `INSTAGRAM_APP_SECRET` — Meta app secret for webhook signature verification
- `INSTAGRAM_WEBHOOK_VERIFY_TOKEN` — non-default verify token
- `CORS_ORIGINS` — explicit HTTPS origins; never `*` with credentials
- `WEBHOOK_SIGNATURE_BYPASS=false`
- `OPENAI_API_KEY` — required when `LLM_MODE=live`

## Webhook signature

In staging/production, POST `/api/v1/webhooks/instagram` rejects requests when the app secret is missing or the signature is invalid.

Development may set `WEBHOOK_SIGNATURE_BYPASS=true` only when `APP_ENV` is `local`, `development`, or `test`.

## Failed job payload redaction

Failed job APIs return `redacted_payload` only. Sensitive keys (tokens, emails, phones, secrets) are masked via `app.core.log_masking`.

## RBAC

Failed job list/retry/ignore requires shop `owner` or `admin` role.
