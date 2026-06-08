from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_shop_membership, require_shop_role
from app.db.session import get_db_session
from app.domain.enums import UserRole
from app.domain.models import ShopMember, User
from app.schemas.recovery import RecoveryRuleCreate, RecoveryRuleRead, RecoveryRuleUpdate
from app.services.order_recovery_service import OrderRecoveryService

router = APIRouter(prefix="/shops/{shop_id}/recovery-rules", tags=["recovery"])


@router.get("", response_model=list[RecoveryRuleRead])
def list_recovery_rules(
    shop_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
    db: Annotated[Session, Depends(get_db_session)],
) -> list[RecoveryRuleRead]:
    return OrderRecoveryService(db).list_rules(shop_id, current_user)


@router.post("", response_model=RecoveryRuleRead, status_code=201)
def create_recovery_rule(
    shop_id: UUID,
    payload: RecoveryRuleCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    _: Annotated[ShopMember, Depends(require_shop_role(UserRole.OPERATOR))],
    db: Annotated[Session, Depends(get_db_session)],
) -> RecoveryRuleRead:
    return OrderRecoveryService(db).create_rule(shop_id, payload, current_user)


@router.patch("/{rule_id}", response_model=RecoveryRuleRead)
def update_recovery_rule(
    shop_id: UUID,
    rule_id: UUID,
    payload: RecoveryRuleUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    _: Annotated[ShopMember, Depends(require_shop_role(UserRole.OPERATOR))],
    db: Annotated[Session, Depends(get_db_session)],
) -> RecoveryRuleRead:
    return OrderRecoveryService(db).update_rule(shop_id, rule_id, payload, current_user)


@router.delete("/{rule_id}", status_code=204)
def delete_recovery_rule(
    shop_id: UUID,
    rule_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _: Annotated[ShopMember, Depends(require_shop_role(UserRole.OPERATOR))],
    db: Annotated[Session, Depends(get_db_session)],
) -> Response:
    OrderRecoveryService(db).delete_rule(shop_id, rule_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
