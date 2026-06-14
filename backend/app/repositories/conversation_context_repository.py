from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.domain.models import ConversationContextItem, ConversationReferenceLink


class ConversationContextRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add_item(self, item: ConversationContextItem) -> ConversationContextItem:
        self.db.add(item)
        self.db.flush()
        return item

    def add_link(self, link: ConversationReferenceLink) -> ConversationReferenceLink:
        self.db.add(link)
        self.db.flush()
        return link

    def list_recent(
        self,
        shop_id: UUID,
        conversation_id: UUID,
        limit: int = 10,
    ) -> list[ConversationContextItem]:
        now = datetime.now(timezone.utc)
        rows = self.db.scalars(
            select(ConversationContextItem)
            .where(
                ConversationContextItem.shop_id == shop_id,
                ConversationContextItem.conversation_id == conversation_id,
                (ConversationContextItem.expires_at.is_(None))
                | (ConversationContextItem.expires_at > now),
            )
            .order_by(ConversationContextItem.created_at.desc())
            .limit(limit)
        ).all()
        return list(rows)

    def expire_stale(self, shop_id: UUID, older_than: datetime) -> int:
        rows = self.db.scalars(
            select(ConversationContextItem).where(
                ConversationContextItem.shop_id == shop_id,
                ConversationContextItem.expires_at.is_(None),
                ConversationContextItem.created_at < older_than,
                ConversationContextItem.item_type.not_in(
                    {"order_summary", "product_post", "product_card"}
                ),
            )
        ).all()
        now = datetime.now(timezone.utc)
        for row in rows:
            row.expires_at = now
        return len(rows)

    def delete_for_conversation(self, shop_id: UUID, conversation_id: UUID) -> None:
        self.db.execute(
            delete(ConversationReferenceLink).where(
                ConversationReferenceLink.shop_id == shop_id,
                ConversationReferenceLink.conversation_id == conversation_id,
            )
        )
        self.db.execute(
            delete(ConversationContextItem).where(
                ConversationContextItem.shop_id == shop_id,
                ConversationContextItem.conversation_id == conversation_id,
            )
        )
