# Catalog Intelligence + Variant Resolver

## Overview

This sprint adds a catalog normalization pipeline, hybrid Qdrant retrieval, advanced variant resolution with confidence scoring, resolver trace logging, and an operator feedback loop.

## Architecture

```
Import / Reindex
    → CatalogNormalizationService (title, brand, color, aliases)
    → CatalogReindexService (dense + sparse Qdrant points)
    → products + variants collections

Resolve Product
    → media_product_links
    → product_aliases exact/partial match
    → CatalogProductSearchService hybrid_search (RRF/DBSF + business rerank)
    → ResolverTraceService

Resolve Variant
    → product inference (optional)
    → VariantResolver deterministic match
    → variant hybrid search fallback
    → ResolverTraceService

Operator Feedback
    → resolver_feedback table
    → optional alias promotion from corrections
```

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/catalog/import` | Batch import with resumable checkpoints |
| POST | `/api/v1/catalog/reindex` | Safe Qdrant reindex by shop/product |
| GET | `/api/v1/catalog/products` | List normalized catalog entries |
| PATCH | `/api/v1/catalog/products/{id}/aliases` | Add/remove product aliases |
| POST | `/api/v1/resolve/product` | Hybrid product resolution |
| POST | `/api/v1/resolve/variant` | Ranked variant resolution |
| GET | `/api/v1/resolve/{trace_id}` | Inspect resolver trace |
| POST | `/api/v1/resolve/{trace_id}/feedback` | Operator correction loop |

## Database Tables

- `products_normalized` — normalized taxonomy + Qdrant metadata
- `product_aliases` / `variant_aliases` — multilingual alias store
- `catalog_import_jobs` — resumable import/reindex jobs
- `resolver_traces` — candidate lists, rules, missing slots
- `resolver_feedback` — operator accept/correct actions
- `brand_size_maps` — brand-specific size normalization
- `media_product_links` — shared post / media → product links

## Qdrant Collections

- **products** — dense vectors + sparse text payload, filtered by `shop_id`, `gender`, `collection`, `status`
- **variants** — per-variant vectors with SKU/color/size metadata

Hybrid fusion utilities live in `app/integrations/catalog_hybrid_search.py` with configurable RRF/DBSF and business reranking hooks.

## Tenant Confidence Thresholds

Per-shop overrides stored in `shop.agent_settings.catalog_intelligence.confidence_thresholds`:

```json
{
  "high": 0.85,
  "medium": 0.55
}
```

## Indexing Safety

- Import/reindex jobs persist `checkpoint.next_index` for resume
- Batch commits every `catalog_import_batch_size` / `catalog_reindex_batch_size` rows
- Failed rows increment `failed_rows` without aborting the whole job

## Benchmarks

Run locally:

```bash
cd backend
python -m app.scripts.run_resolver_benchmark
```

CI runs the same harness after pytest and writes `benchmark-report.json`.

## Frontend

- **Catalog Copilot** (`/catalog-copilot`) — import, reindex, search, alias editing
- **Resolver trace viewer** — inspect candidates, rules, missing slots
- **Why this variant?** — rationale panel tied to trace data
- **Operator correction UI** — submit feedback against a trace
