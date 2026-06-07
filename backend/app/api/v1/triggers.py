from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_shop_membership
from app.db.session import get_db_session
from app.domain.models import ShopMember, User
from app.schemas.triggers import TriggerMatchRequest, TriggerMatchResponse, TriggerPerformanceRead, TriggerRuleCreate, TriggerRuleRead, TriggerRuleUpdate
from app.services.trigger_service import TriggerService

router = APIRouter(prefix="/shops/{shop_id}/triggers", tags=["triggers"])


@router.get("", response_model=list[TriggerRuleRead])
def list_triggers(shop_id: UUID, current_user: Annotated[User, Depends(get_current_user)], _membership: Annotated[ShopMember, Depends(get_shop_membership)], db: Annotated[Session, Depends(get_db_session)]) -> list[TriggerRuleRead]:
    return TriggerService(db).list_rules(shop_id, current_user)


@router.post("", response_model=TriggerRuleRead, status_code=201)
def create_trigger(shop_id: UUID, payload: TriggerRuleCreate, current_user: Annotated[User, Depends(get_current_user)], _membership: Annotated[ShopMember, Depends(get_shop_membership)], db: Annotated[Session, Depends(get_db_session)]) -> TriggerRuleRead:
    return TriggerService(db).create_rule(shop_id, payload, current_user)


@router.patch("/{trigger_id}", response_model=TriggerRuleRead)
def update_trigger(shop_id: UUID, trigger_id: UUID, payload: TriggerRuleUpdate, current_user: Annotated[User, Depends(get_current_user)], _membership: Annotated[ShopMember, Depends(get_shop_membership)], db: Annotated[Session, Depends(get_db_session)]) -> TriggerRuleRead:
    return TriggerService(db).update_rule(shop_id, trigger_id, payload, current_user)


@router.delete("/{trigger_id}", status_code=204)
def delete_trigger(shop_id: UUID, trigger_id: UUID, current_user: Annotated[User, Depends(get_current_user)], _membership: Annotated[ShopMember, Depends(get_shop_membership)], db: Annotated[Session, Depends(get_db_session)]) -> Response:
    TriggerService(db).delete_rule(shop_id, trigger_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/performance", response_model=list[TriggerPerformanceRead])
def trigger_performance(shop_id: UUID, current_user: Annotated[User, Depends(get_current_user)], _membership: Annotated[ShopMember, Depends(get_shop_membership)], db: Annotated[Session, Depends(get_db_session)]) -> list[TriggerPerformanceRead]:
    return TriggerService(db).performance(shop_id, current_user)


@router.post("/match", response_model=TriggerMatchResponse)
def match_trigger(shop_id: UUID, payload: TriggerMatchRequest, current_user: Annotated[User, Depends(get_current_user)], _membership: Annotated[ShopMember, Depends(get_shop_membership)], db: Annotated[Session, Depends(get_db_session)]) -> TriggerMatchResponse:
    return TriggerService(db).match_keyword(shop_id, payload, current_user)
