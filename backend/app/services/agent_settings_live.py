from __future__ import annotations

from typing import Any

from app.domain.enums import SellingStyle


def _as_float(value: Any) -> float:
    return float(value) if value is not None else 0.0


def _enum_value(value: Any) -> Any:
    if isinstance(value, SellingStyle):
        return value.value
    return value


def studio_settings_to_live_overrides(settings: Any) -> dict[str, Any]:
    """Map Agent Studio settings to the legacy live-agent settings contract."""
    return {
        "auto_send_enabled": bool(settings.auto_send_enabled),
        "preview_required_for_low_confidence": bool(settings.preview_required_for_low_confidence),
        "preview_required_for_first_order": bool(settings.preview_required_for_first_order),
        "preview_required_for_high_value_order": bool(settings.preview_required_for_high_value_order),
        "intent_confidence_threshold": _as_float(settings.confidence_threshold_intent),
        "product_confidence_threshold": _as_float(settings.confidence_threshold_product),
        "variant_confidence_threshold": _as_float(settings.confidence_threshold_variant),
        "slots_confidence_threshold": _as_float(settings.confidence_threshold_variant),
        "address_confidence_threshold": _as_float(settings.confidence_threshold_address),
        "auto_send_confidence_threshold": _as_float(settings.confidence_threshold_intent),
        "high_value_order_threshold": _as_float(settings.high_value_order_threshold),
        "brand_voice": settings.brand_voice,
        "selling_style": _enum_value(settings.selling_style),
        "discount_policy_json": settings.discount_policy_json or {},
        "handoff_policy_json": settings.handoff_policy_json or {},
    }


def resolve_live_agent_settings(shop: Any | None) -> dict[str, Any]:
    """Return the settings that the live orchestrator should enforce for a shop."""
    if shop is None:
        return {}
    live_settings = dict(getattr(shop, "agent_settings", {}) or {})
    studio_settings = getattr(shop, "agent_studio_settings", None)
    if studio_settings is not None:
        live_settings.update(studio_settings_to_live_overrides(studio_settings))
    return live_settings
