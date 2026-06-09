from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import rate_limit_webhook
from app.core.config import Settings, get_settings
from app.core.metrics import INBOUND_MESSAGES
from app.db.session import get_db_session
from app.integrations.webhook_signature import verify_meta_signature
from app.schemas.webhook import WebhookAckResponse, WebhookIgnoredResponse
from app.services.webhook_ingestion_service import WebhookIngestionService

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.get("/instagram")
def verify_instagram_webhook(
    settings: Annotated[Settings, Depends(get_settings)],
    hub_mode: Annotated[str | None, Query(alias="hub.mode")] = None,
    hub_verify_token: Annotated[str | None, Query(alias="hub.verify_token")] = None,
    hub_challenge: Annotated[str | None, Query(alias="hub.challenge")] = None,
) -> Response:
    if hub_mode == "subscribe" and hub_verify_token == settings.instagram_webhook_verify_token:
        return Response(content=hub_challenge or "", media_type="text/plain")
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Verification failed")


@router.post("/instagram", response_model=WebhookAckResponse | WebhookIgnoredResponse)
async def receive_instagram_webhook(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    _: Annotated[None, Depends(rate_limit_webhook)],
) -> WebhookAckResponse | WebhookIgnoredResponse:
    body = await request.body()
    if settings.instagram_app_secret:
        signature = request.headers.get("X-Hub-Signature-256")
        if not verify_meta_signature(body, signature, settings.instagram_app_secret):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid webhook signature",
            )

    try:
        import json

        payload: dict[str, Any] = json.loads(body.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        ) from exc

    INBOUND_MESSAGES.inc()
    return WebhookIngestionService(db).handle_instagram_payload(payload, raw_body=body)


@router.post("/meta", response_model=WebhookAckResponse | WebhookIgnoredResponse)
async def receive_meta_webhook(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    _: Annotated[None, Depends(rate_limit_webhook)],
) -> WebhookAckResponse | WebhookIgnoredResponse:
    """Alias for Instagram/Meta webhook ingestion with idempotency."""
    body = await request.body()
    if settings.instagram_app_secret:
        signature = request.headers.get("X-Hub-Signature-256")
        if not verify_meta_signature(body, signature, settings.instagram_app_secret):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid webhook signature",
            )

    try:
        import json

        payload: dict[str, Any] = json.loads(body.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        ) from exc

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload must be a JSON object",
        )

    INBOUND_MESSAGES.inc()
    return WebhookIngestionService(db).handle_instagram_payload(payload, raw_body=body)
