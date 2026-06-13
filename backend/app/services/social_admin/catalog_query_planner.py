from __future__ import annotations
from dataclasses import dataclass, field
import re

@dataclass
class CatalogQueryPlan:
    query_type: str = "unknown"
    category_slug: str | None = None
    brand: str | None = None
    attributes: dict[str, str] = field(default_factory=dict)
    price_min: int | None = None
    price_max: int | None = None
    availability_required: bool = False
    sort: str = "relevance"
    needs_clarification: bool = False
    clarification_question: str | None = None
    confidence: float = 0.0

class CatalogQueryPlanner:
    def __init__(self, categories: dict[str, list[str]] | None = None, brands: list[str] | None = None, attributes: dict[str, list[str]] | None = None) -> None:
        self.categories = categories or {"hammer":["hammer","hammers","چکش"], "shoe":["shoe","shoes","کفش"], "perfume":["perfume","عطر"]}
        self.brands = brands or ["Bosch", "Nike", "بوش"]
        self.attributes = attributes or {"color":["white","black","سفید","مشکی"], "size":["40","۴۰"]}

    def plan(self, text: str, provider: str = "instagram", shop_id: str | None = None, context: object | None = None) -> CatalogQueryPlan:
        raw = text or ""; low = raw.lower(); plan = CatalogQueryPlan()
        if any(w in low for w in ["available","موجود"]): plan.availability_required = True
        if any(w in low for w in ["best seller","پرفروش"]): plan.query_type="best_sellers"; plan.sort="best_seller"; plan.confidence=.9
        if any(w in low for w in ["similar","مشابه"]): plan.query_type="similar_products"; plan.confidence=.82
        if any(w in low for w in ["cheaper","ارزون","ارزان"]): plan.query_type="price_range"; plan.sort="price_asc"; plan.confidence=.8
        m = re.search(r"(?:under|زیر)\s*([\d۰-۹,]+)", low)
        if m:
            plan.price_max = int(m.group(1).translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")).replace(",","")); plan.query_type="price_range"; plan.confidence=.9
        for slug, aliases in self.categories.items():
            if any(a.lower() in low for a in aliases): plan.category_slug=slug; plan.query_type = plan.query_type if plan.query_type!="unknown" else "category_listing"; plan.confidence=max(plan.confidence,.86)
        for brand in self.brands:
            if brand.lower() in low:
                plan.brand = "Bosch" if brand == "بوش" else brand; plan.query_type="brand_listing" if not plan.category_slug else plan.query_type; plan.confidence=max(plan.confidence,.88)
        for name, vals in self.attributes.items():
            for v in vals:
                if v.lower() in low: plan.attributes[name]=v; plan.query_type="attribute_search"; plan.confidence=max(plan.confidence,.84)
        if plan.query_type == "unknown":
            plan.needs_clarification=True; plan.clarification_question="Which category, brand, price range, or attribute should I search?"; plan.confidence=.2
        return plan
