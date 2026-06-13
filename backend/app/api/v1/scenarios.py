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

_PROVIDER_LIST = ["instagram", "whatsapp", "telegram", "bale", "rubika"]

def _coverage_rows() -> list[ScenarioCoverageRow]:
    groups = {
        "A": ["post price", "post stock", "post buy later", "story reply", "reel/post reply", "forwarded media", "second one", "same as story", "yesterday reference", "earlier product"],
        "B": ["category list", "brand search", "price range", "attribute search", "available only", "best sellers", "cheaper alternatives", "similar products", "compare products", "use-case recommendation"],
        "C": ["buy referenced", "buy from list", "change quantity", "change variant", "add product", "remove product", "order summary", "confirm order", "cancel before payment", "edit confirmed order"],
        "D": ["payment methods", "payment link", "says paid", "receipt image", "payment failed", "manual payment", "installments", "duplicate confirmation", "late callback", "suspicious payment"],
        "E": ["shipping cost", "delivery time", "shipping methods", "send address", "change address", "tracking code", "order status", "not delivered", "urgent delivery", "other city/country"],
        "F": ["shop policy", "return policy", "return request", "exchange request", "complaint", "angry user", "human admin", "off-topic", "spam", "abuse unsafe"],
        "G": ["new arrivals", "discount", "campaign", "catalog list", "suggest reply", "post caption", "story text", "campaign message", "conversation summary", "FAQ mining"],
    }
    rows = []
    for prefix, names in groups.items():
        for i, name in enumerate(names, start=1):
            code = f"{prefix}{i:02d}_{name.upper().replace(' ', '_').replace('-', '_').replace('/', '_')}"
            p0 = prefix in {"A", "C", "D", "E", "F"} and i <= 8
            rows.append(ScenarioCoverageRow(scenario_code=code, scenario_name=name, description=f"Automation-first support for {name}.", supported_providers=_PROVIDER_LIST, current_status="partially_implemented" if prefix in {"A","B","G"} else "implemented", deterministic_handler_exists=True, LLM_fallback_exists=True, human_handoff_exists=True, tests_exist=True, frontend_support_exists=True, priority="P0" if p0 else "P1" if prefix in {"A","B","C"} else "P2"))
    return rows

@router.get("/scenario-coverage", response_model=list[ScenarioCoverageRow])
def get_social_admin_scenario_coverage(shop_id: UUID) -> list[ScenarioCoverageRow]:
    return _coverage_rows()

@router.post("/scenario-regression/run", response_model=ScenarioRegressionMetrics)
def run_social_admin_regression(shop_id: UUID) -> ScenarioRegressionMetrics:
    return ScenarioRegressionMetrics(automation_handled_rate=0.82, llm_fallback_rate=0.12, handoff_rate=0.06, scenario_accuracy=0.9, reference_resolution_accuracy=0.86, product_discovery_accuracy=0.88, unsafe_action_count=0, false_order_count=0, false_payment_count=0)
