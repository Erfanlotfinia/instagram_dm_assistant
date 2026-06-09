from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.enums import OrderCorrectnessAction, ShopStatus
from app.domain.models import Order, PilotSettings, Shop
from app.repositories.pilot_mode_repository import PilotModeRepository
from app.services.order_audit_service import OrderAuditService
from app.services.pilot_service import PilotService


@dataclass
class PolicyEvaluation:
    allowed: bool
    reasons: list[str] = field(default_factory=list)
    snapshot: dict[str, Any] = field(default_factory=dict)


class ActionPolicyService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.pilot_modes = PilotModeRepository(db)
        self.audit = OrderAuditService(db)
        self.pilot_service = PilotService(db)

    def evaluate(
        self,
        order: Order | None,
        shop: Shop,
        action: OrderCorrectnessAction,
        *,
        record_attempt: bool = True,
    ) -> PolicyEvaluation:
        reasons: list[str] = []
        snapshot: dict[str, Any] = {"action": action.value, "shop_id": str(shop.id)}

        if shop.status != ShopStatus.ACTIVE:
            reasons.append("tenant_not_active")

        pilot_settings = self.pilot_service.get_or_create_settings(shop.id)
        if pilot_settings.emergency_stop_enabled:
            reasons.append("pilot_emergency_stop")

        self.pilot_modes.ensure_defaults(shop.id)
        pilot_mode = self.pilot_modes.get_for_action(shop.id, action)
        if pilot_mode is None or not pilot_mode.permitted:
            reasons.append("pilot_action_not_permitted")

        snapshot["pilot_enabled"] = pilot_settings.pilot_enabled
        snapshot["emergency_stop"] = pilot_settings.emergency_stop_enabled

        if order is not None and pilot_mode is not None:
            threshold = Decimal(str(pilot_mode.confidence_threshold))
            if order.confidence_score is not None:
                score = Decimal(str(order.confidence_score))
                snapshot["confidence_score"] = float(score)
                snapshot["confidence_threshold"] = float(threshold)
                if score < threshold:
                    reasons.append("confidence_below_threshold")

            if pilot_mode.require_customer_confirmation or action in {
                OrderCorrectnessAction.PAYMENT_LINK,
                OrderCorrectnessAction.COMPLETE,
            }:
                if order.customer_confirmed_at is None:
                    reasons.append("customer_confirmation_required")

        allowed = len(reasons) == 0
        evaluation = PolicyEvaluation(allowed=allowed, reasons=reasons, snapshot=snapshot)

        if order is not None and record_attempt:
            self.audit.record_action_attempt(
                order,
                action,
                allowed,
                denial_reasons=reasons if not allowed else None,
                policy_snapshot=snapshot,
            )

        return evaluation

    def build_pilot_snapshot(self, shop_id: UUID) -> dict[str, Any]:
        settings = self.pilot_service.get_or_create_settings(shop_id)
        return {
            "pilot_enabled": settings.pilot_enabled,
            "pilot_name": settings.pilot_name,
            "emergency_stop": settings.emergency_stop_enabled,
            "require_operator_approval": settings.require_operator_approval_for_first_50_orders,
        }
