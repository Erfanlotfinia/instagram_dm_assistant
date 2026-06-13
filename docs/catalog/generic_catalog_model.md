# Generic catalog model

The Catalog Commerce Assistant represents product facts as generic category attributes instead of fashion-only fields. `color` and `size` remain supported, but they are compatibility attributes inside the Fashion and clothing preset.

Core tables:
- `product_categories` for system and shop categories.
- `catalog_attribute_definitions` for typed attributes such as storage, shade, weight, color, or size.
- `product_attributes` for product-level facts.
- `variant_attributes` for option/variant-defining facts.
- `attribute_aliases` for Persian, English, slang, typo, and shop-specific normalization.
- `category_presets` for onboarding templates.
