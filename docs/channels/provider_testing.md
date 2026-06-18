# provider testing

This document is part of the Modira AI Social Media Admin OS release package.

## Scope

Covers Instagram, WhatsApp Business Platform, Telegram Bot API, Bale Bot API, and Rubika Bot API using the shared channel-agnostic commerce/order engine.

## Verification status

- Instagram: existing implementation retained; mocked/local tests cover parsing and webhook behavior.
- WhatsApp: implemented with mocked tests; real-provider sandbox verification still required.
- Telegram: implemented with mocked tests; real-provider sandbox verification still required.
- Bale: implemented with mocked tests; real-provider sandbox verification still required.
- Rubika: implemented with mocked tests; real-provider sandbox verification still required.

## Security requirements

Provider credentials must be encrypted at rest, redacted from API responses, logs, failed jobs, and debug payloads. Provider webhooks must use the strongest available validation for each provider. Production deployments must not use missing or unsafe webhook secrets.

## Testing requirements

Run backend tests, migrations, frontend typecheck/lint/test/build, and Docker smoke testing before pilot. Where real credentials are unavailable, mocked tests are not a substitute for sandbox validation.
