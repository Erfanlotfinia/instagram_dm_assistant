from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.models import ShopAgentSettings, User
from app.schemas.agent_settings import AutoSendDecisionRead, AutoSendDecisionRequest, ShopAgentStudioSettingsUpdate
from app.services.agent_settings_live import studio_settings_to_live_overrides
from app.services.shop_service import ShopService


class AgentSettingsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.shop_service = ShopService(db)

    def get_or_create(self, shop_id: UUID, user: User) -> ShopAgentSettings:
        self.shop_service.get_shop(shop_id, user)
        settings = self.db.get(ShopAgentSettings, shop_id)
        if settings is None:
            settings = ShopAgentSettings(shop_id=shop_id)
            self.db.add(settings)
            self.db.commit()
            self.db.refresh(settings)
        return settings

    def update(self, shop_id: UUID, payload: ShopAgentStudioSettingsUpdate, user: User) -> ShopAgentSettings:
        settings = self.get_or_create(shop_id, user)
        for field, value in payload.model_dump(exclude_unset=True).items():
            if field == "discount_policy_json" and value:
                value = self._sanitize_discount_policy(value)
            setattr(settings, field, value)
        if settings.shop is not None:
            settings.shop.agent_settings = {
                **(settings.shop.agent_settings or {}),
                **studio_settings_to_live_overrides(settings),
            }
        self.db.commit()
        self.db.refresh(settings)
        return settings

    def decide_auto_send(self, shop_id: UUID, payload: AutoSendDecisionRequest, user: User) -> AutoSendDecisionRead:
        settings = self.get_or_create(shop_id, user)
        reasons: list[str] = []
        if not settings.auto_send_enabled:
            reasons.append("Auto-send is disabled")
        if settings.preview_required_for_low_confidence:
            if payload.intent_confidence < float(settings.confidence_threshold_intent):
                reasons.append("Intent confidence is below threshold")
            if payload.product_confidence < float(settings.confidence_threshold_product):
                reasons.append("Product confidence is below threshold")
            if payload.variant_confidence < float(settings.confidence_threshold_variant):
                reasons.append("Variant confidence is below threshold")
            if payload.address_confidence < float(settings.confidence_threshold_address):
                reasons.append("Address confidence is below threshold")
        if settings.preview_required_for_first_order and payload.is_first_order:
            reasons.append("First order requires preview")
        if settings.preview_required_for_high_value_order and Decimal(payload.order_total) >= Decimal(settings.high_value_order_threshold) > 0:
            reasons.append("High-value order requires preview")
        return AutoSendDecisionRead(auto_send_allowed=not reasons and settings.auto_send_enabled, preview_required=bool(reasons), reasons=reasons)

    def _sanitize_discount_policy(self, policy: dict) -> dict:
        # Keep only explicit admin-provided discount rules; never infer generated discounts from LLM text.
        allowed = policy.get("allowed_discounts", []) if isinstance(policy, dict) else []
        return {"allowed_discounts": allowed, "llm_may_create_discount": False}
