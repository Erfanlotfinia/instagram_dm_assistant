from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.enums import ConversationEventType
from app.domain.models import ConversationEvent
from app.repositories.conversation_event_repository import ConversationEventRepository

EVENT_TITLES: dict[ConversationEventType, str] = {
    ConversationEventType.INBOUND_MESSAGE: "Inbound message received",
    ConversationEventType.OUTBOUND_MESSAGE: "Outbound message sent",
    ConversationEventType.SUGGESTED_REPLY_CREATED: "Suggested reply created",
    ConversationEventType.SUGGESTED_REPLY_APPROVED: "Suggested reply approved",
    ConversationEventType.PRODUCT_RESOLVED: "Product resolved",
    ConversationEventType.VARIANT_RESOLVED: "Variant resolved",
    ConversationEventType.INVENTORY_CHECKED: "Inventory checked",
    ConversationEventType.DRAFT_ORDER_CREATED: "Draft order created",
    ConversationEventType.CUSTOMER_INFO_COMPLETED: "Customer info completed",
    ConversationEventType.CONFIRMATION_REQUESTED: "Confirmation requested",
    ConversationEventType.PAYMENT_LINK_SENT: "Payment link sent",
    ConversationEventType.PAYMENT_RECEIVED: "Payment received",
    ConversationEventType.ORDER_SHIPPED: "Order shipped",
    ConversationEventType.HANDOFF_REQUIRED: "Handoff required",
    ConversationEventType.OPERATOR_TOOK_OVER: "Operator took over",
    ConversationEventType.OPERATOR_RELEASED_AGENT: "Operator released to agent",
    ConversationEventType.ORDER_CANCELLED: "Order cancelled",
    ConversationEventType.CONVERSATION_ASSIGNED: "Conversation assigned",
    ConversationEventType.CUSTOMER_PROFILE_UPDATED: "Customer profile updated",
}


class ConversationEventService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.events = ConversationEventRepository(db)

    def record(
        self,
        conversation_id: UUID,
        event_type: ConversationEventType,
        *,
        title: str | None = None,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
        created_by_user_id: UUID | None = None,
    ) -> ConversationEvent:
        event = ConversationEvent(
            conversation_id=conversation_id,
            event_type=event_type,
            title=title or EVENT_TITLES.get(event_type, event_type.value),
            description=description,
            event_metadata=metadata,
            created_by_user_id=created_by_user_id,
        )
        return self.events.create(event)

    def list_for_conversation(self, conversation_id: UUID) -> list[ConversationEvent]:
        return self.events.list_for_conversation(conversation_id)
