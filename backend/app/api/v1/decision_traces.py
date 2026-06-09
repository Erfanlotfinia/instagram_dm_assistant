from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_shop_membership
from app.db.session import get_db_session
from app.domain.models import AgentDecisionTrace, Conversation, ShopMember, User
from app.schemas.risk import AgentDecisionTraceRead

router = APIRouter(prefix="/shops/{shop_id}", tags=["decision-traces"])


@router.get("/decision-traces", response_model=list[AgentDecisionTraceRead])
def list_shop_decision_traces(shop_id: UUID, _user: Annotated[User, Depends(get_current_user)], _membership: Annotated[ShopMember, Depends(get_shop_membership)], db: Annotated[Session, Depends(get_db_session)]) -> list[AgentDecisionTrace]:
    return list(db.scalars(select(AgentDecisionTrace).join(Conversation).where(Conversation.shop_id == shop_id).order_by(AgentDecisionTrace.created_at.desc())).all())


@router.get("/decision-traces/{trace_id}", response_model=AgentDecisionTraceRead)
def get_shop_decision_trace(shop_id: UUID, trace_id: UUID, _user: Annotated[User, Depends(get_current_user)], _membership: Annotated[ShopMember, Depends(get_shop_membership)], db: Annotated[Session, Depends(get_db_session)]) -> AgentDecisionTrace:
    trace = db.get(AgentDecisionTrace, trace_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="Decision trace not found")
    conversation = db.get(Conversation, trace.conversation_id)
    if conversation is None or conversation.shop_id != shop_id:
        raise HTTPException(status_code=404, detail="Decision trace not found")
    return trace


@router.get("/conversations/{conversation_id}/decision-traces", response_model=list[AgentDecisionTraceRead])
def list_conversation_decision_traces(shop_id: UUID, conversation_id: UUID, _user: Annotated[User, Depends(get_current_user)], _membership: Annotated[ShopMember, Depends(get_shop_membership)], db: Annotated[Session, Depends(get_db_session)]) -> list[AgentDecisionTrace]:
    conversation = db.get(Conversation, conversation_id)
    if not conversation or conversation.shop_id != shop_id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return list(db.scalars(select(AgentDecisionTrace).where(AgentDecisionTrace.conversation_id == conversation_id).order_by(AgentDecisionTrace.created_at.desc())).all())
