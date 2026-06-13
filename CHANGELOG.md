# Changelog

## 1.0.0 - 2026-06-13

### Release positioning
- Prepared the repository metadata and documentation for the Multi-channel Catalog Commerce Assistant v1.0.0 release gate.
- Documents the channel-agnostic commerce engine with Instagram, WhatsApp, Telegram, Bale, and Rubika provider adapters.

### Verification status
- Frontend typecheck, lint, tests, and production build pass in this environment.
- Backend import/startup smoke passes, but the full backend pytest and Alembic gates require a reachable PostgreSQL service and could not complete in this container because Docker and local PostgreSQL are unavailable.
- Docker Compose verification is pending in an environment with Docker installed.

### Known limitations
- Real provider sandbox credentials were not available; provider status is mocked-test verified only until sandbox runs are completed.
- v1.0.0 production release must not be approved until PostgreSQL-backed backend tests, migrations, and Docker smoke tests pass.
