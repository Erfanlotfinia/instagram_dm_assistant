from uuid import UUID

from pydantic import BaseModel


class MessageReceivedJob(BaseModel):
    message_id: UUID
    conversation_id: UUID
    shop_id: UUID
    instagram_account_id: UUID
    customer_id: UUID
    webhook_event_id: UUID | None = None
