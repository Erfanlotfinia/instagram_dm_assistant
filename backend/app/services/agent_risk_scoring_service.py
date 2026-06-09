from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Literal

RiskLevel = Literal["low", "medium", "high", "critical"]

PAYMENT_DISPUTE_TERMS = (
    "payment dispute", "charged", "refund", "پول کم شد", "پرداخت نشد", "مغایرت پرداخت"
)
COMPLAINT_TERMS = ("angry", "complaint", "furious", "ناراضی", "شکایت", "خراب", "اشتباه")


@dataclass(frozen=True)
class AgentRiskScoringInput:
    intent_confidence: float
    slot_confidence: float
    product_confidence: float
    variant_confidence: float
    address_confidence: float
    order_value: Decimal = Decimal("0")
    customer_history: dict[str, Any] = field(default_factory=dict)
    message_text: str | None = None
    sentiment: str | None = None
    complaint_flag: bool = False
    previous_failed_attempts: int = 0
    unavailable_variant: bool = False
    payment_related_message: bool = False
    settings: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentRiskScore:
    risk_level: RiskLevel
    risk_reasons: list[str]
    requires_handoff: bool
    requires_preview: bool
    score: float

    def model_dump(self) -> dict[str, Any]:
        return {
            "risk_level": self.risk_level,
            "risk_reasons": self.risk_reasons,
            "requires_handoff": self.requires_handoff,
            "requires_preview": self.requires_preview,
            "score": self.score,
        }


class AgentRiskScoringService:
    """Deterministic, auditable risk gate for LLM-assisted message processing."""

    def score(self, payload: AgentRiskScoringInput) -> AgentRiskScore:
        settings = payload.settings or {}
        reasons: list[str] = []
        score = 0.0
        requires_handoff = False
        requires_preview = False
        text = (payload.message_text or "").lower()

        def add(points: float, reason: str) -> None:
            nonlocal score
            score += points
            reasons.append(reason)

        if payload.payment_related_message or any(term in text for term in PAYMENT_DISPUTE_TERMS):
            add(1.0, "payment_dispute_requires_handoff")
            requires_handoff = True
        if payload.complaint_flag or payload.sentiment == "angry" or any(term in text for term in COMPLAINT_TERMS):
            add(0.9, "angry_or_complaint_requires_handoff")
            requires_handoff = True

        thresholds = {
            "intent": float(settings.get("intent_confidence_threshold", 0.75)),
            "slot": float(settings.get("slot_confidence_threshold", 0.75)),
            "product": float(settings.get("product_confidence_threshold", 0.80)),
            "variant": float(settings.get("variant_confidence_threshold", 0.85)),
            "address": float(settings.get("address_confidence_threshold", 0.80)),
        }
        confidences = {
            "intent": payload.intent_confidence,
            "slot": payload.slot_confidence,
            "product": payload.product_confidence,
            "variant": payload.variant_confidence,
            "address": payload.address_confidence,
        }
        for label, value in confidences.items():
            if float(value) < thresholds[label]:
                add(0.15 if label != "variant" else 0.25, f"low_{label}_confidence:{float(value):.2f}< {thresholds[label]:.2f}")
                requires_preview = True
                if label == "variant" and settings.get("handoff_for_low_variant_confidence", False):
                    requires_handoff = True

        if payload.unavailable_variant:
            add(0.35, "unavailable_variant")
            requires_preview = True
        if payload.previous_failed_attempts > 0:
            add(min(0.3, payload.previous_failed_attempts * 0.1), "previous_failed_attempts")
        if payload.customer_history.get("chargebacks", 0) or payload.customer_history.get("prior_handoffs", 0) >= 2:
            add(0.3, "risky_customer_history")
            requires_preview = True

        high_value_threshold = Decimal(str(settings.get("high_value_order_threshold", "500")))
        if high_value_threshold > 0 and payload.order_value >= high_value_threshold:
            add(0.35, "high_value_order_requires_preview")
            requires_preview = True

        score = min(score, 1.0)
        if requires_handoff and score >= 0.9:
            level: RiskLevel = "critical"
        elif score >= 0.7:
            level = "high"
        elif score >= 0.3:
            level = "medium"
        else:
            level = "low"

        if level == "critical":
            requires_handoff = True
            requires_preview = True
        elif level == "high" and settings.get("handoff_for_high_risk", False):
            requires_handoff = True
        elif level == "high":
            requires_preview = True

        return AgentRiskScore(level, reasons, requires_handoff, requires_preview, round(score, 4))
