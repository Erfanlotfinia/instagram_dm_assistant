# Catalog Guide

Modira represents product facts as **generic category attributes**, not hard-coded fashion fields. `color` and `size` remain supported as ordinary attributes inside category presets — they are not platform-wide assumptions.

**Related docs:** [catalog-intelligence-architecture.md](./catalog-intelligence-architecture.md) (import pipeline, Qdrant, resolver traces), [api-documentation.md](./api-documentation.md) (REST routes), [admin-guide.md](./admin-guide.md) (shop setup checklist).

---

## Data model

Core tables:

| Table | Purpose |
|-------|---------|
| `product_categories` | System and shop categories |
| `catalog_attribute_definitions` | Typed attributes (storage, shade, weight, color, size, etc.) |
| `product_attributes` | Product-level facts |
| `variant_attributes` | Option / variant-defining facts |
| `attribute_aliases` | Persian, English, slang, typo, and shop-specific normalization |
| `category_presets` | Onboarding templates for common verticals |

Normalized search and resolver metadata also use `products_normalized`, `product_aliases`, `variant_aliases`, and `catalog_import_jobs` (see [catalog-intelligence-architecture.md](./catalog-intelligence-architecture.md)).

---

## Category presets

System presets include:

- Clothing and apparel
- Shoes and bags
- Electronics
- Cosmetics and beauty
- Home and decoration
- Food and grocery
- Books and media
- Digital products
- General product

**Fashion** is a first-class preset with `color`, `size`, `material`, `fit`, `gender`, and `season` — but it is no longer the only product model. Any vertical can define its own attribute set through presets and definitions.

---

## Attribute dictionary

The attribute dictionary is Modira's generic catalog-attribute normalization layer.

**Precedence:** shop aliases override system aliases. Category-scoped aliases can normalize values like `۱۲۸ گیگ` → `128GB`, cosmetics shades, food weights, clothing colors/sizes, formats, materials, and other product facts.

**Admin UI:** **Catalog → Attributes**

---

## Product import

Catalog imports map CSV/JSON columns to:

- Title, description, category, price, SKU, stock, images
- Generic product or variant attributes

Import jobs are tracked through `catalog_import_jobs` with resumable checkpoints.

| Action | Route / UI |
|--------|------------|
| Batch import | `POST /api/v1/catalog/import` or **Catalog → Products** |
| Reindex after bulk import | `POST /api/v1/catalog/reindex` |
| List normalized entries | `GET /api/v1/catalog/products` |

Reindex is required after bulk import so Qdrant hybrid search stays in sync.

---

## Resolver

Product and variant resolution is **deterministic first**, with hybrid search fallback.

| Stage | Behavior |
|-------|----------|
| LLM extraction | Extracts raw requested attributes only — no variant selection |
| Backend normalization | `AttributeDictionary` + aliases normalize extracted values |
| Variant match | Deterministic match against `variant_attributes` |
| Legacy compatibility | `raw_color` and `raw_size` requests continue through the compatibility resolver |
| Search fallback | Hybrid Qdrant search when deterministic match is inconclusive |

**Admin UI:** **Catalog → Resolver** (test bench before go-live)

Resolver traces, confidence thresholds, and operator feedback are documented in [catalog-intelligence-architecture.md](./catalog-intelligence-architecture.md).

---

## Catalog quality

Quality checks should flag:

- Products without categories or images
- Variants without SKUs
- Duplicate SKUs
- Missing price or stock
- Missing required attributes
- Conflicting aliases
- Unmapped import columns
- Unindexed products (stale Qdrant state)

Run reindex and review import job `failed_rows` after bulk changes.

---

## Admin hub routes

| Route | Purpose |
|-------|---------|
| `/catalog/products` | Product and variant management |
| `/catalog/attributes` | Attribute dictionary |
| `/catalog/resolver` | Resolver test bench |
| `/catalog/mapping` | Link Instagram post URLs to products |
| `/catalog-copilot` | Import, reindex, search, alias editing (advanced) |

---

## API quick reference

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/v1/catalog/import` | Batch import with resumable checkpoints |
| `POST` | `/api/v1/catalog/reindex` | Safe Qdrant reindex by shop/product |
| `GET` | `/api/v1/catalog/products` | List normalized catalog entries |
| `PATCH` | `/api/v1/catalog/products/{id}/aliases` | Add/remove product aliases |
| `POST` | `/api/v1/resolve/product` | Hybrid product resolution |
| `POST` | `/api/v1/resolve/variant` | Ranked variant resolution |
| `GET` | `/api/v1/resolve/{trace_id}` | Inspect resolver trace |
| `POST` | `/api/v1/resolve/{trace_id}/feedback` | Operator correction loop |

Full request/response schemas: [api-documentation.md](./api-documentation.md).
