from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_shop_membership
from app.db.session import get_db_session
from app.domain.models import ShopAgentSettings, ShopMember, User
from app.schemas.risk import AgentRiskSettingsRead, AgentRiskSettingsUpdate

router = APIRouter(prefix="/shops/{shop_id}/agent-risk-settings", tags=["agent-risk-settings"])

DEFAULT_POLICY = {
    "handoff_for_high_risk": False,
    "handoff_for_low_variant_confidence": False,
}


def _get_or_create(db: Session, shop_id: UUID) -> ShopAgentSettings:
    settings = db.get(ShopAgentSettings, shop_id)
    if settings is None:
        settings = ShopAgentSettings(shop_id=shop_id)
        db.add(settings)
        db.flush()
    return settings


def _read(settings: ShopAgentSettings) -> AgentRiskSettingsRead:
    policy = {**DEFAULT_POLICY, **(settings.risk_policy_json or {})}
    return AgentRiskSettingsRead(
        shop_id=settings.shop_id,
        intent_confidence_threshold=float(settings.confidence_threshold_intent),
        slot_confidence_threshold=float(settings.confidence_threshold_variant),
        product_confidence_threshold=float(settings.confidence_threshold_product),
        variant_confidence_threshold=float(settings.confidence_threshold_variant),
        address_confidence_threshold=float(settings.confidence_threshold_address),
        high_value_order_threshold=float(settings.high_value_order_threshold),
        handoff_for_high_risk=bool(policy["handoff_for_high_risk"]),
        handoff_for_low_variant_confidence=bool(policy["handoff_for_low_variant_confidence"]),
        preview_required_for_high_value_order=settings.preview_required_for_high_value_order,
    )


@router.get("", response_model=AgentRiskSettingsRead)
def get_agent_risk_settings(shop_id: UUID, _user: Annotated[User, Depends(get_current_user)], _membership: Annotated[ShopMember, Depends(get_shop_membership)], db: Annotated[Session, Depends(get_db_session)]) -> AgentRiskSettingsRead:
    return _read(_get_or_create(db, shop_id))


@router.put("", response_model=AgentRiskSettingsRead)
def update_agent_risk_settings(shop_id: UUID, payload: AgentRiskSettingsUpdate, _user: Annotated[User, Depends(get_current_user)], _membership: Annotated[ShopMember, Depends(get_shop_membership)], db: Annotated[Session, Depends(get_db_session)]) -> AgentRiskSettingsRead:
    settings = _get_or_create(db, shop_id)
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
    db.commit()
    db.refresh(settings)
    return _read(settings)
