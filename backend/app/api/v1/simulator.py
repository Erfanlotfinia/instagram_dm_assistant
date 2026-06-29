from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_shop_membership, require_shop_role
from app.db.session import get_db_session
from app.domain.enums import UserRole
from app.domain.models import ShopMember, User
from app.schemas.replay import ReplayRunRequest, ReplayRunResponse, SimulatorRunDetailRead, SimulatorRunItemRead, SimulatorRunSummaryRead
from app.schemas.simulator import (
    DMSimulatorRequest,
    DMSimulatorResponse,
    SimulatorResetResponse,
    SimulatorRunSummary,
)
from app.services.dm_simulator_service import DMSimulatorService
from app.services.replay_engine import ReplayEngine

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


@router.post("/replay", response_model=ReplayRunResponse)
def replay_simulator(
    shop_id: UUID,
    payload: ReplayRunRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.ADMIN))],
    db: Annotated[Session, Depends(get_db_session)],
) -> ReplayRunResponse:
    run = ReplayEngine(db).run(shop_id, payload, current_user)
    items = list(run.items)
    return ReplayRunResponse(
        run=SimulatorRunDetailRead(
            **SimulatorRunSummaryRead.model_validate(run).model_dump(),
            items=[SimulatorRunItemRead.model_validate(item) for item in items],
            catalog_snapshot_json=run.catalog_snapshot_json,
        )
    )


@router.get("/runs", response_model=list[SimulatorRunSummaryRead | SimulatorRunSummary])
def list_simulator_runs(
    shop_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
    db: Annotated[Session, Depends(get_db_session)],
    legacy: bool = Query(default=False),
) -> list[SimulatorRunSummaryRead | SimulatorRunSummary]:
    if legacy:
        return DMSimulatorService(db).list_runs(shop_id, current_user)
    return [SimulatorRunSummaryRead.model_validate(run) for run in ReplayEngine(db).list_runs(shop_id)]


@router.get("/runs/{run_id}", response_model=SimulatorRunDetailRead)
def get_simulator_run(
    shop_id: UUID,
    run_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
    db: Annotated[Session, Depends(get_db_session)],
) -> SimulatorRunDetailRead:
    run = ReplayEngine(db).get_run(shop_id, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Simulator run not found")
    return SimulatorRunDetailRead(
        **SimulatorRunSummaryRead.model_validate(run).model_dump(),
        items=[SimulatorRunItemRead.model_validate(item) for item in run.items],
        catalog_snapshot_json=run.catalog_snapshot_json,
    )


@router.delete("/reset", response_model=SimulatorResetResponse)
def reset_simulator(
    shop_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
    db: Annotated[Session, Depends(get_db_session)],
) -> SimulatorResetResponse:
    deleted = DMSimulatorService(db).reset(shop_id, current_user)
    return SimulatorResetResponse(deleted_conversations=deleted)
