from __future__ import annotations

import json
from typing import Annotated, Any
from uuid import UUID

from sqlalchemy import select
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.api.deps import get_current_user, rate_limit_webhook, require_shop_role
from app.db.session import get_db_session
from app.domain.enums import ChannelProvider, UserRole
from app.domain.models import ChannelAccount, ShopMember, User
from app.schemas.channels import (
    ChannelAccountCreate,
    ChannelAccountRead,
    WebhookTestResponse,
)
from app.schemas.webhook import WebhookAckResponse, WebhookIgnoredResponse
from app.services.channel_account_service import (
    ChannelAccountService,
    adapter_for_provider,
)
from app.services.channel_webhook_ingestion_service import (
    ChannelWebhookIngestionService,
)
from app.services.shop_service import ShopService

router = APIRouter(tags=["channels"])


def _default_telegram_webhook_url(channel_account_id: UUID) -> str:
    return (
        f"{get_settings().api_public_base_url}"
        f"/api/v1/channels/telegram/{channel_account_id}/webhook"
    )


def _resolve_telegram_webhook_account(
    db: Session, request: Request, channel_account_id: UUID | None = None
) -> ChannelAccount | None:
    if channel_account_id:
        return db.scalar(
            select(ChannelAccount).where(
                ChannelAccount.provider == ChannelProvider.TELEGRAM,
                ChannelAccount.id == channel_account_id,
            )
        )
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if not secret:
        return None
    return db.scalar(
        select(ChannelAccount).where(
            ChannelAccount.provider == ChannelProvider.TELEGRAM,
            ChannelAccount.webhook_secret == secret,
        )
    )


@router.get("/shops/{shop_id}/channels", response_model=list[ChannelAccountRead])
def list_channel_accounts(
    shop_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
) -> list[ChannelAccountRead]:
    ShopService(db).get_shop(shop_id, current_user)
    return [
        ChannelAccountRead.model_validate(account)
        for account in ChannelAccountService(db).list_for_shop(shop_id)
    ]


@router.post(
    "/shops/{shop_id}/channels", response_model=ChannelAccountRead, status_code=201
)
def create_channel_account(
    shop_id: UUID,
    payload: ChannelAccountCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.ADMIN))],
    db: Annotated[Session, Depends(get_db_session)],
) -> ChannelAccountRead:
    ShopService(db).get_shop(shop_id, current_user)
    return ChannelAccountRead.model_validate(
        ChannelAccountService(db).create(shop_id, payload)
    )


@router.post(
    "/shops/{shop_id}/channels/{channel_account_id}/webhook-test",
    response_model=WebhookTestResponse,
)
def test_channel_webhook(
    shop_id: UUID,
    channel_account_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
) -> WebhookTestResponse:
    account = ChannelAccountService(db).get(shop_id, channel_account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Channel account not found")
    return WebhookTestResponse(provider=account.provider, channel_account_id=account.id)


@router.get("/channels/{provider}/webhook")
def verify_channel_webhook(
    provider: ChannelProvider,
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    hub_mode: Annotated[str | None, Query(alias="hub.mode")] = None,
    hub_verify_token: Annotated[str | None, Query(alias="hub.verify_token")] = None,
    hub_challenge: Annotated[str | None, Query(alias="hub.challenge")] = None,
) -> Response:
    if (
        provider in {ChannelProvider.INSTAGRAM, ChannelProvider.WHATSAPP}
        and hub_mode == "subscribe"
    ):
        if provider == ChannelProvider.WHATSAPP:
            account = db.scalar(
                select(ChannelAccount).where(
                    ChannelAccount.provider == ChannelProvider.WHATSAPP,
                    ChannelAccount.webhook_verify_token == hub_verify_token,
                )
            )
            if account:
                return Response(content=hub_challenge or "", media_type="text/plain")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Verification failed"
            )
        return (
            Response(content=hub_challenge or "", media_type="text/plain")
            if hub_verify_token
            else Response(status_code=403)
        )
    return Response(content="ok", media_type="text/plain")


@router.post(
    "/channels/{provider}/webhook",
    response_model=WebhookAckResponse | WebhookIgnoredResponse,
)
async def receive_channel_webhook(
    provider: ChannelProvider,
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    _: Annotated[None, Depends(rate_limit_webhook)],
) -> WebhookAckResponse | WebhookIgnoredResponse:
    return await _receive_channel_webhook(provider, request, db)


@router.post(
    "/channels/telegram/{channel_account_id}/webhook",
    response_model=WebhookAckResponse | WebhookIgnoredResponse,
)
async def receive_telegram_channel_webhook(
    channel_account_id: UUID,
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    _: Annotated[None, Depends(rate_limit_webhook)],
) -> WebhookAckResponse | WebhookIgnoredResponse:
    return await _receive_channel_webhook(
        ChannelProvider.TELEGRAM, request, db, channel_account_id=channel_account_id
    )


async def _receive_channel_webhook(
    provider: ChannelProvider,
    request: Request,
    db: Session,
    channel_account_id: UUID | None = None,
) -> WebhookAckResponse | WebhookIgnoredResponse:
    body = await request.body()
    try:
        payload: dict[str, Any] = json.loads(body.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload"
        ) from exc
    account: ChannelAccount | None = None
    if provider == ChannelProvider.WHATSAPP:
        phone_number_id = None
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                phone_number_id = (change.get("value", {}).get("metadata") or {}).get(
                    "phone_number_id"
                )
                if phone_number_id:
                    break
        account = db.scalar(
            select(ChannelAccount).where(
                ChannelAccount.provider == provider,
                ChannelAccount.phone_number_id == phone_number_id,
            )
        )
    elif provider == ChannelProvider.TELEGRAM:
        account = _resolve_telegram_webhook_account(db, request, channel_account_id)
        if channel_account_id and not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Telegram channel account not found",
            )
    adapter = adapter_for_provider(provider, account)
    settings = get_settings()
    if (
        provider == ChannelProvider.WHATSAPP
        and settings.requires_webhook_signature
        and (not account or not account.webhook_secret)
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="WhatsApp app secret is required for webhook signature verification",
        )
    if (
        provider == ChannelProvider.TELEGRAM
        and settings.requires_webhook_signature
        and (
            not account
            or not account.webhook_secret
            or request.headers.get("X-Telegram-Bot-Api-Secret-Token")
            != account.webhook_secret
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid Telegram webhook secret token",
        )
    if not await adapter.verify_webhook(request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid webhook signature or secret",
        )
    return ChannelWebhookIngestionService(db).handle_payload(
        provider,
        payload,
        dict(request.headers),
        channel_account_id=account.id if account else None,
    )


@router.post(
    "/webhooks/{provider}", response_model=WebhookAckResponse | WebhookIgnoredResponse
)
async def receive_provider_compat_webhook(
    provider: ChannelProvider,
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    _: Annotated[None, Depends(rate_limit_webhook)],
) -> WebhookAckResponse | WebhookIgnoredResponse:
    return await _receive_channel_webhook(provider, request, db)


@router.post("/shops/{shop_id}/channels/{channel_account_id}/telegram/set-webhook")
async def set_telegram_webhook(
    shop_id: UUID,
    channel_account_id: UUID,
    payload: dict[str, Any],
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.ADMIN))],
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, Any]:
    ShopService(db).get_shop(shop_id, current_user)
    account = ChannelAccountService(db).get(shop_id, channel_account_id)
    if not account or account.provider != ChannelProvider.TELEGRAM:
        raise HTTPException(
            status_code=404, detail="Telegram channel account not found"
        )
    return await adapter_for_provider(
        ChannelProvider.TELEGRAM, account
    ).configure_webhook(
        payload.get("url") or _default_telegram_webhook_url(account.id),
        account.webhook_secret,
    )


@router.post("/shops/{shop_id}/channels/{channel_account_id}/telegram/delete-webhook")
async def delete_telegram_webhook(
    shop_id: UUID,
    channel_account_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.ADMIN))],
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, Any]:
    ShopService(db).get_shop(shop_id, current_user)
    account = ChannelAccountService(db).get(shop_id, channel_account_id)
    if not account or account.provider != ChannelProvider.TELEGRAM:
        raise HTTPException(
            status_code=404, detail="Telegram channel account not found"
        )
    return await adapter_for_provider(
        ChannelProvider.TELEGRAM, account
    ).delete_webhook()


@router.get("/shops/{shop_id}/channels/{channel_account_id}/telegram/webhook-info")
async def get_telegram_webhook_info(
    shop_id: UUID,
    channel_account_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, Any]:
    ShopService(db).get_shop(shop_id, current_user)
    account = ChannelAccountService(db).get(shop_id, channel_account_id)
    if not account or account.provider != ChannelProvider.TELEGRAM:
        raise HTTPException(
            status_code=404, detail="Telegram channel account not found"
        )
    return await adapter_for_provider(
        ChannelProvider.TELEGRAM, account
    ).get_webhook_info()
