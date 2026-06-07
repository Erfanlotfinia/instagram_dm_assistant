from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.config import Settings, get_settings
from app.domain.enums import AgentIntent
from app.schemas.agent import AgentExtractionResult
from app.services.slot_merge_service import has_provided_slot_values

HANDOFF_INTENTS = {AgentIntent.HUMAN_HELP, AgentIntent.TRACK_ORDER}
COMPLAINT_KEYWORDS = ("شکایت", "ناراضی", "خراب", "اشتباه", "complaint", "angry", "refund")
PAYMENT_KEYWORDS = ("پرداخت نشد", "پول کم شد", "payment failed", "charged")


@dataclass
class HandoffDecision:
    required: bool
    reason: str | None = None


def evaluate_handoff(
    extraction: AgentExtractionResult,
    *,
    failure_count: int,
    settings: Settings | None = None,
    variant_mismatch: bool = False,
    payment_issue: bool = False,
    high_value_order: bool = False,
    address_ambiguous: bool = False,
    order_total: float | None = None,
    shop_settings: dict[str, Any] | None = None,
) -> HandoffDecision:
    settings = settings or get_settings()
    shop_settings = shop_settings or {}
    intent_threshold = float(shop_settings.get("intent_confidence_threshold", settings.agent_intent_confidence_threshold))
    slots_threshold = float(shop_settings.get("slots_confidence_threshold", settings.agent_slots_confidence_threshold))
    address_threshold = float(shop_settings.get("address_confidence_threshold", 0.75))
    high_value_threshold = float(shop_settings.get("high_value_order_threshold", 500.0))

    text = " ".join(str(value or "") for value in (extraction.human_reason, extraction.reply_style_hint)).lower()
    if extraction.needs_human and extraction.human_reason:
        return HandoffDecision(required=True, reason=extraction.human_reason)
    if extraction.intent in HANDOFF_INTENTS:
        return HandoffDecision(required=True, reason=f"Unsupported or escalated intent: {extraction.intent.value}")
    if any(keyword in text for keyword in COMPLAINT_KEYWORDS):
        return HandoffDecision(required=True, reason="Customer complaint detected")
    if payment_issue or any(keyword in text for keyword in PAYMENT_KEYWORDS):
        return HandoffDecision(required=True, reason="Payment issue detected")
    if variant_mismatch:
        return HandoffDecision(required=True, reason="Variant mismatch requires operator review")
    if high_value_order or (order_total is not None and order_total >= high_value_threshold):
        return HandoffDecision(required=True, reason="High-value order requires approval")
    if address_ambiguous or extraction.confidence.address < address_threshold:
        return HandoffDecision(required=True, reason=f"Address confidence below threshold ({extraction.confidence.address:.2f})")
    if extraction.confidence.intent < intent_threshold:
        return HandoffDecision(required=True, reason=f"Low intent confidence ({extraction.confidence.intent:.2f})")
    if has_provided_slot_values(extraction) and extraction.confidence.slots < slots_threshold:
        return HandoffDecision(required=True, reason=f"Low slot confidence ({extraction.confidence.slots:.2f})")
    if failure_count > settings.agent_max_failures:
        return HandoffDecision(required=True, reason=f"Repeated unclear messages or agent failures ({failure_count})")
    return HandoffDecision(required=False)
