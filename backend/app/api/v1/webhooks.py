"""Compatibility aliases for the canonical channel webhook endpoints.

New provider integrations must use ``/api/v1/channels/{provider}/webhook``.
These routes intentionally contain no verification, parsing, or business logic.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.orm import Session

from app.api.deps import rate_limit_webhook
from app.api.v1.channels import _receive_channel_webhook, verify_channel_webhook
from app.db.session import get_db_session
from app.domain.enums import ChannelProvider
from app.schemas.webhook import WebhookAckResponse, WebhookIgnoredResponse

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.get("/instagram", deprecated=True)
def verify_instagram_webhook_compat(
    db: Annotated[Session, Depends(get_db_session)],
    hub_mode: Annotated[str | None, Query(alias="hub.mode")] = None,
    hub_verify_token: Annotated[str | None, Query(alias="hub.verify_token")] = None,
    hub_challenge: Annotated[str | None, Query(alias="hub.challenge")] = None,
) -> Response:
    return verify_channel_webhook(
        ChannelProvider.INSTAGRAM.value,
        db,
        hub_mode,
        hub_verify_token,
        hub_challenge,
    )


@router.post(
    "/instagram",
    response_model=WebhookAckResponse | WebhookIgnoredResponse,
    deprecated=True,
)
async def receive_instagram_webhook_compat(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    _: Annotated[None, Depends(rate_limit_webhook)],
) -> WebhookAckResponse | WebhookIgnoredResponse:
    return await _receive_channel_webhook(
        ChannelProvider.INSTAGRAM,
        request,
        db,
        allow_legacy_meta_secret=True,
    )


@router.post(
    "/meta",
    response_model=WebhookAckResponse | WebhookIgnoredResponse,
    deprecated=True,
)
async def receive_meta_webhook_compat(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    _: Annotated[None, Depends(rate_limit_webhook)],
) -> WebhookAckResponse | WebhookIgnoredResponse:
    return await _receive_channel_webhook(
        ChannelProvider.INSTAGRAM,
        request,
        db,
        allow_legacy_meta_secret=True,
    )
