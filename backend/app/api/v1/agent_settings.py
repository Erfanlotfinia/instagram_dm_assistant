from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_shop_membership
from app.db.session import get_db_session
from app.domain.models import ShopMember, User
from app.schemas.agent_settings import AutoSendDecisionRead, AutoSendDecisionRequest, ShopAgentStudioSettingsRead, ShopAgentStudioSettingsUpdate
from app.services.agent_settings_service import AgentSettingsService

router = APIRouter(prefix="/shops/{shop_id}/agent-studio-settings", tags=["agent-settings"])


@router.get("", response_model=ShopAgentStudioSettingsRead)
def get_settings(shop_id: UUID, current_user: Annotated[User, Depends(get_current_user)], _membership: Annotated[ShopMember, Depends(get_shop_membership)], db: Annotated[Session, Depends(get_db_session)]) -> ShopAgentStudioSettingsRead:
    return AgentSettingsService(db).get_or_create(shop_id, current_user)


@router.patch("", response_model=ShopAgentStudioSettingsRead)
def update_settings(shop_id: UUID, payload: ShopAgentStudioSettingsUpdate, current_user: Annotated[User, Depends(get_current_user)], _membership: Annotated[ShopMember, Depends(get_shop_membership)], db: Annotated[Session, Depends(get_db_session)]) -> ShopAgentStudioSettingsRead:
    return AgentSettingsService(db).update(shop_id, payload, current_user)


@router.post("/auto-send-decision", response_model=AutoSendDecisionRead)
def auto_send_decision(shop_id: UUID, payload: AutoSendDecisionRequest, current_user: Annotated[User, Depends(get_current_user)], _membership: Annotated[ShopMember, Depends(get_shop_membership)], db: Annotated[Session, Depends(get_db_session)]) -> AutoSendDecisionRead:
    return AgentSettingsService(db).decide_auto_send(shop_id, payload, current_user)
