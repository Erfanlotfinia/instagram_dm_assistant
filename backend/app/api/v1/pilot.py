from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_shop_membership, require_shop_role
from app.db.session import get_db_session
from app.domain.enums import UserRole
from app.domain.models import ShopMember, User
from app.schemas.pilot import (
    PilotActionResponse,
    PilotEventLogRead,
    PilotMetricsRead,
    PilotReadinessResponse,
    PilotSettingsRead,
    PilotSettingsUpdate,
)
from app.services.pilot_service import PilotService

router = APIRouter(prefix="/shops/{shop_id}", tags=["pilot"])


@router.get("/pilot-settings", response_model=PilotSettingsRead)
def get_pilot_settings(
    shop_id: UUID,
    _current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
    db: Annotated[Session, Depends(get_db_session)],
) -> PilotSettingsRead:
    service = PilotService(db)
    return service.to_settings_read(service.get_or_create_settings(shop_id))


@router.put("/pilot-settings", response_model=PilotSettingsRead)
def update_pilot_settings(
    shop_id: UUID,
    payload: PilotSettingsUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.ADMIN))],
    db: Annotated[Session, Depends(get_db_session)],
) -> PilotSettingsRead:
    service = PilotService(db)
    return service.to_settings_read(service.update_settings(shop_id, payload, user_id=current_user.id))


@router.get("/pilot-readiness", response_model=PilotReadinessResponse)
def get_pilot_readiness(
    shop_id: UUID,
    _current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
    db: Annotated[Session, Depends(get_db_session)],
    product_mapping_threshold: float = Query(default=0.8, ge=0, le=1),
) -> PilotReadinessResponse:
    return PilotService(db).readiness(shop_id, product_mapping_threshold=product_mapping_threshold)


@router.post("/pilot/emergency-stop", response_model=PilotActionResponse)
def pilot_emergency_stop(
    shop_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.ADMIN))],
    db: Annotated[Session, Depends(get_db_session)],
) -> PilotActionResponse:
    service = PilotService(db)
    settings, event, scope_preview = service.set_emergency_stop(shop_id, True, user_id=current_user.id)
    return PilotActionResponse(pilot_settings=service.to_settings_read(settings), event=service.to_event_read(event))


@router.post("/pilot/resume", response_model=PilotActionResponse)
def pilot_resume(
    shop_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.ADMIN))],
    db: Annotated[Session, Depends(get_db_session)],
) -> PilotActionResponse:
    service = PilotService(db)
    settings, event, _scope = service.set_emergency_stop(shop_id, False, user_id=current_user.id)
    return PilotActionResponse(pilot_settings=service.to_settings_read(settings), event=service.to_event_read(event))


@router.get("/pilot/metrics", response_model=PilotMetricsRead)
def get_pilot_metrics(
    shop_id: UUID,
    _current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
    db: Annotated[Session, Depends(get_db_session)],
) -> PilotMetricsRead:
    return PilotService(db).metrics(shop_id)


@router.get("/pilot/events", response_model=PilotEventLogRead)
def get_pilot_events(
    shop_id: UUID,
    _current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
    db: Annotated[Session, Depends(get_db_session)],
    limit: int = Query(default=50, ge=1, le=200),
) -> PilotEventLogRead:
    service = PilotService(db)
    return PilotEventLogRead(events=[service.to_event_read(event) for event in service.list_events(shop_id, limit=limit)])
