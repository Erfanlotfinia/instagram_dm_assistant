from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from app.domain.enums import AgentMode
from app.domain.models import ShopAgentSettings


@dataclass(frozen=True)
class AutoSendDecisionInput:
    settings: ShopAgentSettings
    intent_confidence: float
    product_confidence: float
    variant_confidence: float
    address_confidence: float
    order_value: Decimal = Decimal("0")
    is_first_order: bool = False
    handoff_reason: str | None = None
    message_risk: str | None = None
    customer_history: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AutoSendDecision:
    auto_send_allowed: bool
    requires_preview: bool
    requires_handoff: bool
    reasons: list[str]


class AutoSendDecisionService:
    """Deterministic safety gate for all outbound agent automation."""

    def decide(self, payload: AutoSendDecisionInput) -> AutoSendDecision:
        settings = payload.settings
        reasons: list[str] = []
        requires_preview = False
        requires_handoff = bool(payload.handoff_reason)

        if settings.mode == AgentMode.COPILOT:
            reasons.append("copilot_mode_requires_operator_approval")
            requires_preview = True
        elif settings.mode == AgentMode.HUMAN_FIRST:
            reasons.append("human_first_mode_blocks_auto_send")
            requires_preview = True

        if not settings.auto_send_enabled:
            reasons.append("auto_send_disabled")
            requires_preview = True

        if payload.handoff_reason:
            reasons.append(f"handoff_required:{payload.handoff_reason}")
            requires_preview = True
        if payload.message_risk:
            reasons.append(f"message_risk:{payload.message_risk}")
            requires_preview = True

        if settings.preview_required_for_low_confidence:
            checks = (
                ("intent", payload.intent_confidence, float(settings.confidence_threshold_intent)),
                ("product", payload.product_confidence, float(settings.confidence_threshold_product)),
                ("variant", payload.variant_confidence, float(settings.confidence_threshold_variant)),
                ("address", payload.address_confidence, float(settings.confidence_threshold_address)),
            )
            for label, value, threshold in checks:
                if float(value) < threshold:
                    reasons.append(f"low_{label}_confidence:{float(value):.2f}< {threshold:.2f}")
                    requires_preview = True

        threshold = Decimal(settings.high_value_order_threshold or 0)
        if settings.preview_required_for_high_value_order and threshold > 0 and payload.order_value >= threshold:
            reasons.append("high_value_order_requires_preview")
            requires_preview = True

        if settings.preview_required_for_first_order and payload.is_first_order:
            reasons.append("first_order_requires_preview")
            requires_preview = True

        controlled = settings.mode == AgentMode.CONTROLLED_AUTOPILOT
        auto_send_allowed = controlled and settings.auto_send_enabled and not requires_preview and not requires_handoff
        return AutoSendDecision(
            auto_send_allowed=auto_send_allowed,
            requires_preview=requires_preview,
            requires_handoff=requires_handoff,
            reasons=reasons,
        )
