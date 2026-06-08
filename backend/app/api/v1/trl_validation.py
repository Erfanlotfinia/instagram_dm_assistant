from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_shop_membership
from app.db.session import get_db_session
from app.domain.models import ShopMember, User
from app.schemas.trl_validation import (
    TRLValidationResetResponse,
    TRLValidationRunRead,
    TRLValidationRunRequest,
    TRLValidationScenarioResultRead,
)
from app.services.trl_validation_runner import TRLValidationRunner

router = APIRouter(prefix="/shops/{shop_id}/trl-validation", tags=["trl-validation"])


@router.post("/run", response_model=TRLValidationRunRead)
def run_trl_validation(
    shop_id: UUID,
    payload: TRLValidationRunRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
    db: Annotated[Session, Depends(get_db_session)],
) -> TRLValidationRunRead:
    return TRLValidationRunner(db).run(shop_id, created_by_user_id=current_user.id, reset_demo_data=payload.reset_demo_data, scenario_limit=payload.scenario_limit)


@router.get("/runs", response_model=list[TRLValidationRunRead])
def list_trl_validation_runs(
    shop_id: UUID,
    _current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
    db: Annotated[Session, Depends(get_db_session)],
) -> list[TRLValidationRunRead]:
    return TRLValidationRunner(db).list_runs(shop_id)


@router.get("/runs/{run_id}", response_model=TRLValidationRunRead)
def get_trl_validation_run(
    shop_id: UUID,
    run_id: UUID,
    _current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
    db: Annotated[Session, Depends(get_db_session)],
) -> TRLValidationRunRead:
    run = TRLValidationRunner(db).get_run(shop_id, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="TRL validation run not found")
    return run


@router.get("/runs/{run_id}/scenarios", response_model=list[TRLValidationScenarioResultRead])
def list_trl_validation_scenarios(
    shop_id: UUID,
    run_id: UUID,
    _current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
    db: Annotated[Session, Depends(get_db_session)],
    passed: bool | None = Query(default=None),
) -> list[TRLValidationScenarioResultRead]:
    return TRLValidationRunner(db).list_results(shop_id, run_id, passed=passed)


@router.delete("/reset", response_model=TRLValidationResetResponse)
def reset_trl_validation(
    shop_id: UUID,
    _current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
    db: Annotated[Session, Depends(get_db_session)],
) -> TRLValidationResetResponse:
    return TRLValidationRunner(db).reset(shop_id)
