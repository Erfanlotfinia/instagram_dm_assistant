from pydantic import BaseModel


class WebhookAckResponse(BaseModel):
    status: str = "ok"


class WebhookIgnoredResponse(BaseModel):
    status: str = "ignored"
    reason: str | None = None
