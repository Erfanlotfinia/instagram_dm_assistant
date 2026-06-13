# Generic resolver

LLMs extract raw requested attributes only. Backend services normalize attributes and select variants using deterministic `variant_attributes`. Legacy `raw_color` and `raw_size` requests continue through the compatibility resolver.
