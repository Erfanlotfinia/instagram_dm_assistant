from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.models import ShopAgentSettings
from app.schemas.risk import AgentRiskSettingsUpdate


class AgentRiskSettingsService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_or_create(self, shop_id: UUID) -> ShopAgentSettings:
        settings = self.db.get(ShopAgentSettings, shop_id)
        if settings is None:
            settings = ShopAgentSettings(shop_id=shop_id)
            self.db.add(settings)
            self.db.flush()
        return settings

    def update(self, shop_id: UUID, payload: AgentRiskSettingsUpdate) -> ShopAgentSettings:
        settings = self.get_or_create(shop_id)
        data = payload.model_dump(exclude_unset=True)
        if "intent_confidence_threshold" in data:
            settings.confidence_threshold_intent = data.pop("intent_confidence_threshold")
        if "slot_confidence_threshold" in data:
            settings.confidence_threshold_variant = data.pop("slot_confidence_threshold")
        if "product_confidence_threshold" in data:
            settings.confidence_threshold_product = data.pop("product_confidence_threshold")
        if "variant_confidence_threshold" in data:
            settings.confidence_threshold_variant = data.pop("variant_confidence_threshold")
        if "address_confidence_threshold" in data:
            settings.confidence_threshold_address = data.pop("address_confidence_threshold")
        if "high_value_order_threshold" in data:
            settings.high_value_order_threshold = data.pop("high_value_order_threshold")
        if "preview_required_for_high_value_order" in data:
            settings.preview_required_for_high_value_order = data.pop("preview_required_for_high_value_order")
        policy = {**(settings.risk_policy_json or {})}
        for key in ("handoff_for_high_risk", "handoff_for_low_variant_confidence"):
            if key in data:
                policy[key] = data[key]
        settings.risk_policy_json = policy
        self.db.commit()
        self.db.refresh(settings)
        return settings
