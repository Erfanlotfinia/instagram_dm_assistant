from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.models import ShopAgentSettings, User
from app.schemas.agent_settings import AutoSendDecisionRead, AutoSendDecisionRequest, ShopAgentStudioSettingsUpdate
from app.services.agent_settings_live import studio_settings_to_live_overrides
from app.services.audit_service import AuditService
from app.services.auto_send_decision_service import AutoSendDecisionInput, AutoSendDecisionService
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
        changes = payload.model_dump(exclude_unset=True, mode="json")
        AuditService(self.db).log(
            action="agent_settings_changed",
            entity_type="shop_agent_settings",
            shop_id=shop_id,
            actor_user_id=user.id,
            entity_id=str(shop_id),
            metadata=changes,
        )
        if "mode" in changes:
            AuditService(self.db).log(
                action="agent_mode_changed",
                entity_type="shop_agent_settings",
                shop_id=shop_id,
                actor_user_id=user.id,
                entity_id=str(shop_id),
                metadata={"mode": changes["mode"]},
            )
        threshold_changes = {key: value for key, value in changes.items() if key.startswith("confidence_threshold_")}
        if threshold_changes:
            AuditService(self.db).log(
                action="confidence_threshold_changed",
                entity_type="shop_agent_settings",
                shop_id=shop_id,
                actor_user_id=user.id,
                entity_id=str(shop_id),
                metadata=threshold_changes,
            )
        self.db.commit()
        self.db.refresh(settings)
        return settings

    def decide_auto_send(self, shop_id: UUID, payload: AutoSendDecisionRequest, user: User) -> AutoSendDecisionRead:
        settings = self.get_or_create(shop_id, user)
        decision = AutoSendDecisionService().decide(
            AutoSendDecisionInput(
                settings=settings,
                intent_confidence=payload.intent_confidence,
                product_confidence=payload.product_confidence,
                variant_confidence=payload.variant_confidence,
                address_confidence=payload.address_confidence,
                order_value=Decimal(payload.order_total),
                is_first_order=payload.is_first_order,
                handoff_reason=payload.handoff_reason,
                message_risk=payload.message_risk,
            )
        )
        return AutoSendDecisionRead(
            auto_send_allowed=decision.auto_send_allowed,
            preview_required=decision.requires_preview,
            requires_handoff=decision.requires_handoff,
            reasons=decision.reasons,
        )

    def _sanitize_discount_policy(self, policy: dict) -> dict:
        # Keep only explicit admin-provided discount rules; never infer generated discounts from LLM text.
        allowed = policy.get("allowed_discounts", []) if isinstance(policy, dict) else []
        return {"allowed_discounts": allowed, "llm_may_create_discount": False}
