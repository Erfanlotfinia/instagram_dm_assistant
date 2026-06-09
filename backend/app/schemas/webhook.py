from pydantic import BaseModel


class WebhookAckResponse(BaseModel):
    status: str = "ok"
    dedupe_outcome: str | None = None


class WebhookIgnoredResponse(BaseModel):
    status: str = "ignored"
    reason: str | None = None
    dedupe_outcome: str | None = None
