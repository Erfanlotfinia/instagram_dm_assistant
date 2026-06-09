from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_shop_membership, require_shop_role
from app.db.session import get_db_session
from app.domain.enums import UserRole
from app.domain.models import ShopMember, User
from app.schemas.policy import (
    PolicyCheckResultRead,
    PolicyConfigValidateRequest,
    PolicyConfigValidateResponse,
    PolicyEvaluationResponse,
    PolicyEvaluationSampleRequest,
)
from app.services.policy_engine import PolicyEngine, PolicyEvaluationContext
from app.domain.enums import PilotOperatingMode

router = APIRouter(prefix="/shops/{shop_id}/policies", tags=["policies"])


@router.post("/validate", response_model=PolicyEvaluationResponse)
def validate_policies(
    shop_id: UUID,
    payload: PolicyEvaluationSampleRequest,
    _user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
) -> PolicyEvaluationResponse:
    engine = PolicyEngine()
    valid, errors = engine.validate(payload.config_json)
    if not valid:
        return PolicyEvaluationResponse(
            allowed=False,
            checks=[PolicyCheckResultRead(name=error, passed=False, reason=error, severity="error") for error in errors],
            blocked_actions=["validation_failed"],
        )
    result = engine.evaluate(
        PolicyEvaluationContext(
            shop_id=shop_id,
            operating_mode=PilotOperatingMode(payload.operating_mode),
            intent_confidence=payload.intent_confidence,
            product_confidence=payload.product_confidence,
            variant_confidence=payload.variant_confidence,
            customer_confirmed=payload.customer_confirmed,
            stock_reserved=payload.stock_reserved,
            within_messaging_window=payload.within_messaging_window,
            action_name=payload.action_name,
            requires_write=payload.requires_write,
            handoff_required=payload.handoff_required,
            emergency_stop=payload.emergency_stop,
        ),
        payload.config_json,
    )
    return PolicyEvaluationResponse(
        allowed=result.allowed,
        checks=[PolicyCheckResultRead(**check.__dict__) for check in result.checks],
        blocked_actions=result.blocked_actions,
    )


@router.post("/validate-config", response_model=PolicyConfigValidateResponse)
def validate_policy_config(
    shop_id: UUID,
    payload: PolicyConfigValidateRequest,
    _user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.ADMIN))],
) -> PolicyConfigValidateResponse:
    valid, errors = PolicyEngine().validate(payload.config_json)
    return PolicyConfigValidateResponse(valid=valid, errors=errors)
