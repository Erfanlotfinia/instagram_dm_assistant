from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_shop_membership
from app.db.session import get_db_session
from app.domain.models import ShopMember, User
from app.schemas.simulator import DMSimulatorRequest, DMSimulatorResponse
from app.services.dm_simulator_service import DMSimulatorService

router = APIRouter(prefix="/shops/{shop_id}/simulator", tags=["simulator"])


@router.post("/dm", response_model=DMSimulatorResponse)
def run_dm_simulator(shop_id: UUID, payload: DMSimulatorRequest, current_user: Annotated[User, Depends(get_current_user)], _membership: Annotated[ShopMember, Depends(get_shop_membership)], db: Annotated[Session, Depends(get_db_session)]) -> DMSimulatorResponse:
    return DMSimulatorService(db).run(shop_id, payload, current_user)


@router.delete("/dm")
def reset_dm_simulator(shop_id: UUID, current_user: Annotated[User, Depends(get_current_user)], _membership: Annotated[ShopMember, Depends(get_shop_membership)], db: Annotated[Session, Depends(get_db_session)]) -> dict[str, int]:
    return {"deleted_conversations": DMSimulatorService(db).reset(shop_id, current_user)}
