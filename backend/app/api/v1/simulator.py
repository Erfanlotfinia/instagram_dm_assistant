from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_shop_membership
from app.db.session import get_db_session
from app.domain.models import ShopMember, User
from app.schemas.simulator import (
    DMSimulatorRequest,
    DMSimulatorResponse,
    SimulatorResetResponse,
    SimulatorRunSummary,
)
from app.services.dm_simulator_service import DMSimulatorService

router = APIRouter(prefix="/shops/{shop_id}/simulator", tags=["simulator"])


@router.post("/run", response_model=DMSimulatorResponse)
def run_simulator(
    shop_id: UUID,
    payload: DMSimulatorRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
    db: Annotated[Session, Depends(get_db_session)],
) -> DMSimulatorResponse:
    return DMSimulatorService(db).run(shop_id, payload, current_user)


@router.get("/runs", response_model=list[SimulatorRunSummary])
def list_simulator_runs(
    shop_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
    db: Annotated[Session, Depends(get_db_session)],
) -> list[SimulatorRunSummary]:
    return DMSimulatorService(db).list_runs(shop_id, current_user)


@router.delete("/reset", response_model=SimulatorResetResponse)
def reset_simulator(
    shop_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
    db: Annotated[Session, Depends(get_db_session)],
) -> SimulatorResetResponse:
    deleted = DMSimulatorService(db).reset(shop_id, current_user)
    return SimulatorResetResponse(deleted_conversations=deleted)


# Backward-compatible aliases for earlier Sprint E drafts
@router.post("/dm", response_model=DMSimulatorResponse, include_in_schema=False)
def run_dm_simulator_legacy(
    shop_id: UUID,
    payload: DMSimulatorRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
    db: Annotated[Session, Depends(get_db_session)],
) -> DMSimulatorResponse:
    return DMSimulatorService(db).run(shop_id, payload, current_user)


@router.delete("/dm", response_model=SimulatorResetResponse, include_in_schema=False)
def reset_dm_simulator_legacy(
    shop_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
    db: Annotated[Session, Depends(get_db_session)],
) -> SimulatorResetResponse:
    deleted = DMSimulatorService(db).reset(shop_id, current_user)
    return SimulatorResetResponse(deleted_conversations=deleted)
