from uuid import UUID

from pydantic import BaseModel, ValidationError

from app.domain.enums import ChannelProvider


class InvalidJobPayloadError(Exception):
    """Raised when a job payload cannot be processed and should not be retried."""


class MessageReceivedJob(BaseModel):
    message_id: UUID
    conversation_id: UUID
    shop_id: UUID
    instagram_account_id: UUID | None = None
    channel_provider: ChannelProvider | None = None
    channel_account_id: UUID | None = None
    customer_id: UUID
    webhook_event_id: UUID | None = None


def validate_message_received_payload(payload: dict) -> MessageReceivedJob:
    try:
        return MessageReceivedJob.model_validate(payload)
    except ValidationError as exc:
        missing = [str(err["loc"][0]) for err in exc.errors() if err["type"] == "missing"]
        if missing:
            detail = f"Invalid message_received job payload: missing required fields ({', '.join(missing)})"
        else:
            detail = "Invalid message_received job payload"
        raise InvalidJobPayloadError(detail) from exc
