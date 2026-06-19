# Sprint A — Core Order Agent Hardening

This sprint strengthens catalog order taking with deterministic backend services. The LLM may extract raw fields such as customer color and size text, but backend services normalize those fields, resolve product variants, check stock, return alternatives, and log unavailable demand.

## Added capabilities

- Attribute dictionary tables for catalog aliases, including global defaults and shop-specific overrides.
- `ColorNormalizer` and `SizeNormalizer` services for Persian/English deterministic normalization.
- Variant resolver API for testing backend-only SKU resolution and stock-aware alternatives.
- Unavailable demand log table with raw and normalized customer requests.
- Admin pages for attribute dictionary management, variant resolver testing, and unavailable demand review.

## API endpoints

- `GET /api/v1/shops/{shop_id}/color-aliases`
- `POST /api/v1/shops/{shop_id}/color-aliases`
- `PATCH /api/v1/shops/{shop_id}/color-aliases/{alias_id}`
- `DELETE /api/v1/shops/{shop_id}/color-aliases/{alias_id}`
- `GET /api/v1/shops/{shop_id}/size-aliases`
- `POST /api/v1/shops/{shop_id}/size-aliases`
- `PATCH /api/v1/shops/{shop_id}/size-aliases/{alias_id}`
- `DELETE /api/v1/shops/{shop_id}/size-aliases/{alias_id}`
- `POST /api/v1/shops/{shop_id}/variant-resolver/test`
- `GET /api/v1/shops/{shop_id}/unavailable-demand`

## Local run

```bash
cd backend
alembic upgrade head
pytest app/tests/test_sprint_a_normalization_unit.py
```

```bash
cd frontend
npm run build
```

## Risks / TODOs

- Full database-backed resolver tests require the PostgreSQL test database to be running.
- Conversation detail already stores normalized slots and variant alternatives; additional UI polish can make the decision trace more prominent.
- A future sprint should backfill normalized variant values for old variants that only have raw color/size values.
