from __future__ import annotations

from typing import Any

from app.domain.models import ConversationSlots
from app.schemas.agent import AgentExtractionResult, ExtractedSlots

CUSTOMER_SLOT_FIELDS = ("customer_name", "phone", "city", "address", "postal_code")
VARIANT_SLOT_FIELDS = ("color", "size", "quantity")


def merge_extracted_slots(
    existing: ConversationSlots,
    extraction: AgentExtractionResult,
) -> ConversationSlots:
    merged = _slots_to_dict(existing)
    extracted = extraction.slots.model_dump()

    for field, value in extracted.items():
        if value is not None and value != "":
            merged[field] = value

    if extraction.product_reference.instagram_post_url:
        merged["instagram_post_url"] = extraction.product_reference.instagram_post_url

    for field, value in merged.items():
        setattr(existing, field, value)

    existing.confidence = extraction.confidence.model_dump()
    existing.missing_fields = list(extraction.missing_fields)
    return existing


def slots_to_dict(slots: ConversationSlots) -> dict[str, Any]:
    return _slots_to_dict(slots)


def _slots_to_dict(slots: ConversationSlots) -> dict[str, Any]:
    return {
        "product_id": slots.product_id,
        "product_variant_id": slots.product_variant_id,
        "instagram_post_url": slots.instagram_post_url,
        "color": slots.color,
        "size": slots.size,
        "quantity": slots.quantity,
        "customer_name": slots.customer_name,
        "phone": slots.phone,
        "city": slots.city,
        "address": slots.address,
        "postal_code": slots.postal_code,
    }


def compute_missing_fields(slots: ConversationSlots, *, require_variant: bool) -> list[str]:
    missing: list[str] = []
    if slots.product_id is None:
        missing.append("product")
    if require_variant:
        if not slots.color:
            missing.append("color")
        if not slots.size:
            missing.append("size")
        if slots.quantity is None:
            missing.append("quantity")
    for field in CUSTOMER_SLOT_FIELDS:
        if field == "postal_code":
            continue
        if getattr(slots, field) in (None, ""):
            missing.append(field)
    return missing


def has_provided_slot_values(extraction: AgentExtractionResult) -> bool:
    values = extraction.slots.model_dump()
    return any(value not in (None, "") for value in values.values())


def normalize_variant_value(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned.casefold() if cleaned else None
