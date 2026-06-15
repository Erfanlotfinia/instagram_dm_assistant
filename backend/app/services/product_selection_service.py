from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models import Conversation, ConversationSlots, Product


class ProductSelectionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def select_product(self, shop_id: UUID, conversation_id: UUID, product_id: UUID) -> ConversationSlots:
        conversation = self.db.get(Conversation, conversation_id)
        product = self.db.get(Product, product_id)
        if not conversation or conversation.shop_id != shop_id or not product or product.shop_id != shop_id:
            raise HTTPException(status_code=404, detail="Conversation or product not found")
        slots = self.db.scalar(select(ConversationSlots).where(ConversationSlots.conversation_id == conversation_id))
        if slots is None:
            slots = ConversationSlots(conversation_id=conversation_id)
            self.db.add(slots)
        slots.product_id = product_id
        self.db.commit()
        return slots
