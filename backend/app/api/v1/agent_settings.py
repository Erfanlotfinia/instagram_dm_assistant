from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_shop_membership
from app.db.session import get_db_session
from app.domain.models import ShopMember, User
from app.schemas.agent_settings import (
    AutoSendDecisionRead,
    AutoSendDecisionRequest,
    ShopAgentStudioSettingsRead,
    ShopAgentStudioSettingsUpdate,
)
from app.services.agent_settings_service import AgentSettingsService

router = APIRouter(prefix="/shops/{shop_id}", tags=["agent-settings"])


@router.get("/agent-settings", response_model=ShopAgentStudioSettingsRead)
def get_agent_settings(
    shop_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
    db: Annotated[Session, Depends(get_db_session)],
) -> ShopAgentStudioSettingsRead:
    settings = AgentSettingsService(db).get_or_create(shop_id, current_user)
    return ShopAgentStudioSettingsRead.model_validate(settings)


@router.put("/agent-settings", response_model=ShopAgentStudioSettingsRead)
def put_agent_settings(
    shop_id: UUID,
    payload: ShopAgentStudioSettingsUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
    db: Annotated[Session, Depends(get_db_session)],
) -> ShopAgentStudioSettingsRead:
    settings = AgentSettingsService(db).update(shop_id, payload, current_user)
    return ShopAgentStudioSettingsRead.model_validate(settings)


@router.get("/agent-studio-settings", response_model=ShopAgentStudioSettingsRead)
def get_studio_settings(
    shop_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
    db: Annotated[Session, Depends(get_db_session)],
) -> ShopAgentStudioSettingsRead:
    settings = AgentSettingsService(db).get_or_create(shop_id, current_user)
    return ShopAgentStudioSettingsRead.model_validate(settings)


@router.patch("/agent-studio-settings", response_model=ShopAgentStudioSettingsRead)
def patch_studio_settings(
    shop_id: UUID,
    payload: ShopAgentStudioSettingsUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
    db: Annotated[Session, Depends(get_db_session)],
) -> ShopAgentStudioSettingsRead:
    settings = AgentSettingsService(db).update(shop_id, payload, current_user)
    return ShopAgentStudioSettingsRead.model_validate(settings)


@router.post("/agent-studio-settings/auto-send-decision", response_model=AutoSendDecisionRead)
def auto_send_decision(
    shop_id: UUID,
    payload: AutoSendDecisionRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
    db: Annotated[Session, Depends(get_db_session)],
) -> AutoSendDecisionRead:
    decision = AgentSettingsService(db).decide_auto_send(shop_id, payload, current_user)
    return AutoSendDecisionRead.model_validate(decision)
