# Generic catalog model

Modira represents product facts as generic category attributes. `color` and `size` remain supported as ordinary attributes inside category presets, not as platform-wide assumptions.

Core tables:
- `product_categories` for system and shop categories.
- `catalog_attribute_definitions` for typed attributes such as storage, shade, weight, color, or size.
- `product_attributes` for product-level facts.
- `variant_attributes` for option/variant-defining facts.
- `attribute_aliases` for Persian, English, slang, typo, and shop-specific normalization.
- `category_presets` for onboarding templates.
