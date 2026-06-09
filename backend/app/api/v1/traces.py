from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_shop_membership
from app.db.session import get_db_session
from app.domain.models import ShopMember, User
from app.schemas.trace import AssembledDecisionTraceRead
from app.services.decision_trace_service import DecisionTraceService

router = APIRouter(prefix="/shops/{shop_id}/traces", tags=["traces"])


@router.get("/{trace_id}", response_model=AssembledDecisionTraceRead)
def get_decision_trace(
    shop_id: UUID,
    trace_id: UUID,
    _user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
    db: Annotated[Session, Depends(get_db_session)],
) -> AssembledDecisionTraceRead:
    trace = DecisionTraceService(db).get_assembled_trace(shop_id, trace_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="Decision trace not found")
    return trace
