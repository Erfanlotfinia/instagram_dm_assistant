# Changelog

## 1.0.0 - 2026-06-13

### Added
- Generic catalog attribute normalizer and generic variant resolver with Persian/English alias support.
- Multi-channel provider adapters for Instagram, WhatsApp, Telegram, Bale, and Rubika.
- Generic catalog migration (`20260613_0026_generic_catalog_attributes`).
- Release documentation: `docs/setup.md`, `docs/release/v1.0.0.md`.

### Fixed
- **Route conflict:** legacy `POST /api/v1/webhooks/instagram` was shadowed by `POST /api/v1/webhooks/{provider}`; webhook router is now registered before the channels router so Instagram legacy ingestion works.
- **Failed job retry test:** retry payload now includes all required `message_received` job fields.
- **Test settings isolation:** autouse fixture resets cached `Settings` for webhook bypass and rate-limit test safety.
- **Frontend source test:** skips gracefully when the frontend tree is unavailable (Docker backend-only runs).

### Verified in release audit
- Backend: **357 passed, 1 skipped** (`pytest app/tests -q` in Docker with PostgreSQL).
- Alembic: `alembic upgrade head` succeeds on PostgreSQL.
- Frontend: typecheck, lint, test (46), and build pass.
- Docker Compose: config valid, build succeeds, stack starts, `/health` and `/ready` return ok, worker and scheduler start.

### Known limitations
- Real provider sandbox credentials were not available; all providers are **mocked-test verified only**.
- Frontend source integration test skips inside backend-only Docker containers.
- Scheduler embedding refresh logs errors when `OPENAI_API_KEY` is invalid but continues running.
