from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_shop_membership
from app.db.session import get_db_session
from app.domain.models import AgentDecisionTrace, Conversation, ShopMember, User

router = APIRouter(prefix="/shops/{shop_id}/conversations", tags=["decision-traces"])


@router.get("/{conversation_id}/decision-traces")
def list_decision_traces(shop_id: UUID, conversation_id: UUID, _user: Annotated[User, Depends(get_current_user)], _membership: Annotated[ShopMember, Depends(get_shop_membership)], db: Annotated[Session, Depends(get_db_session)]) -> list[dict]:
    conversation = db.get(Conversation, conversation_id)
    if not conversation or conversation.shop_id != shop_id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    traces = db.scalars(select(AgentDecisionTrace).where(AgentDecisionTrace.conversation_id == conversation_id).order_by(AgentDecisionTrace.created_at.desc())).all()
    return [
        {
            "id": str(trace.id),
            "message_id": str(trace.message_id) if trace.message_id else None,
            "agent_run_id": str(trace.agent_run_id) if trace.agent_run_id else None,
            "intent": trace.intent,
            "extracted_slots": trace.extracted_slots,
            "product_candidates": trace.product_candidates,
            "selected_product_id": str(trace.selected_product_id) if trace.selected_product_id else None,
            "variant_resolution": trace.variant_resolution,
            "inventory_result": trace.inventory_result,
            "order_action": trace.order_action,
            "next_state": trace.next_state,
            "outbound_message_id": str(trace.outbound_message_id) if trace.outbound_message_id else None,
            "auto_send_allowed": trace.auto_send_allowed,
            "human_handoff_required": trace.human_handoff_required,
            "reasoning_summary": trace.reasoning_summary,
            "created_at": trace.created_at.isoformat(),
        }
        for trace in traces
    ]
