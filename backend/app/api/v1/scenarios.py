from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_shop_membership, require_shop_role
from app.db.session import get_db_session
from app.domain.enums import UserRole
from app.domain.models import ShopMember, User
from app.schemas.incident import IncidentRead
from app.schemas.scenario import ScenarioPackCreateRequest, ScenarioPackRead
from app.services.incident_service import IncidentService
from app.services.scenario_pack_service import ScenarioPackService

router = APIRouter(prefix="/shops/{shop_id}", tags=["scenarios", "incidents"])


@router.post("/scenarios", response_model=ScenarioPackRead)
def create_scenario_pack(
    shop_id: UUID,
    payload: ScenarioPackCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.ADMIN))],
    db: Annotated[Session, Depends(get_db_session)],
) -> ScenarioPackRead:
    pack = ScenarioPackService(db).create(shop_id, payload, current_user)
    return ScenarioPackService.to_read(pack)


@router.get("/scenarios", response_model=list[ScenarioPackRead])
def list_scenario_packs(
    shop_id: UUID,
    _user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
    db: Annotated[Session, Depends(get_db_session)],
) -> list[ScenarioPackRead]:
    return [ScenarioPackService.to_read(pack) for pack in ScenarioPackService(db).list_for_shop(shop_id)]


@router.get("/incidents", response_model=list[IncidentRead])
def list_incidents(
    shop_id: UUID,
    _user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
    db: Annotated[Session, Depends(get_db_session)],
    limit: int = 50,
) -> list[IncidentRead]:
    from sqlalchemy import select
    from app.domain.models import Incident

    incidents = list(
        db.scalars(
            select(Incident).where(Incident.shop_id == shop_id).order_by(Incident.opened_at.desc()).limit(limit)
        ).all()
    )
    return [IncidentRead.model_validate(incident) for incident in incidents]


@router.get("/incidents/{incident_id}", response_model=IncidentRead)
def get_incident(
    shop_id: UUID,
    incident_id: UUID,
    _user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
    db: Annotated[Session, Depends(get_db_session)],
) -> IncidentRead:
    incident = IncidentService(db).get_incident(shop_id, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return IncidentRead.model_validate(incident)

from app.schemas.scenario import ScenarioCoverageRow, ScenarioRegressionMetrics
from app.services.social_admin.scenario_coverage_service import ScenarioCoverageService
from app.services.social_admin.scenario_regression_runner import ScenarioRegressionRunner


@router.get("/scenario-coverage", response_model=list[ScenarioCoverageRow])
def get_social_admin_scenario_coverage(
    shop_id: UUID,
    _user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
) -> list[ScenarioCoverageRow]:
    return ScenarioCoverageService().build_rows()

@router.post("/scenario-regression/run", response_model=ScenarioRegressionMetrics)
def run_social_admin_regression(
    shop_id: UUID,
    _user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.ADMIN))],
    db: Annotated[Session, Depends(get_db_session)],
) -> ScenarioRegressionMetrics:
    return ScenarioRegressionRunner(db).run()
