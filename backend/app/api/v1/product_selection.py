from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_shop_membership
from app.db.session import get_db_session
from app.domain.models import Conversation, ConversationSlots, Product, ShopMember, User

router = APIRouter(prefix="/shops/{shop_id}/conversations", tags=["product-selection"])


class ProductSelectionRequest(BaseModel):
    product_id: UUID


@router.post("/{conversation_id}/select-product")
def select_product(shop_id: UUID, conversation_id: UUID, payload: ProductSelectionRequest, _user: Annotated[User, Depends(get_current_user)], _membership: Annotated[ShopMember, Depends(get_shop_membership)], db: Annotated[Session, Depends(get_db_session)]) -> dict:
    conversation = db.get(Conversation, conversation_id)
    product = db.get(Product, payload.product_id)
    if not conversation or conversation.shop_id != shop_id or not product or product.shop_id != shop_id:
        raise HTTPException(status_code=404, detail="Conversation or product not found")
    slots = db.scalar(select(ConversationSlots).where(ConversationSlots.conversation_id == conversation_id))
    if slots is None:
        slots = ConversationSlots(conversation_id=conversation_id)
        db.add(slots)
    slots.product_id = payload.product_id
    db.commit()
    return {"conversation_id": str(conversation_id), "selected_product_id": str(payload.product_id)}
