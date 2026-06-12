from __future__ import annotations

import json
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, rate_limit_webhook, require_shop_role
from app.channels.adapters import (
    BaleProviderAdapter,
    InstagramProviderAdapter,
    RubikaProviderAdapter,
    TelegramProviderAdapter,
    WhatsAppProviderAdapter,
)
from app.db.session import get_db_session
from app.domain.enums import ChannelProvider, UserRole
from app.domain.models import ChannelAccount, ShopMember, User
from app.schemas.channels import ChannelAccountCreate, ChannelAccountRead, WebhookTestResponse
from app.schemas.webhook import WebhookAckResponse, WebhookIgnoredResponse
from app.services.channel_account_service import ChannelAccountService
from app.services.channel_webhook_ingestion_service import ChannelWebhookIngestionService
from app.services.shop_service import ShopService

router = APIRouter(tags=["channels"])


def _account_adapter(account: ChannelAccount):
    if account.provider == ChannelProvider.INSTAGRAM:
        return InstagramProviderAdapter(app_secret=account.webhook_secret)
    if account.provider == ChannelProvider.WHATSAPP:
        return WhatsAppProviderAdapter(
            verify_token=account.webhook_verify_token, webhook_secret=account.webhook_secret
        )
    if account.provider == ChannelProvider.TELEGRAM:
        return TelegramProviderAdapter(webhook_secret=account.webhook_secret)
    if account.provider == ChannelProvider.BALE:
        return BaleProviderAdapter(webhook_secret=account.webhook_secret)
    if account.provider == ChannelProvider.RUBIKA:
        return RubikaProviderAdapter(webhook_secret=account.webhook_secret)
    raise HTTPException(status_code=400, detail="Unsupported provider")


def _instagram_recipient_ids(payload: dict[str, Any]) -> set[str]:
    recipient_ids: set[str] = set()
    for entry in payload.get("entry", []):
        if not isinstance(entry, dict):
            continue
        if entry.get("id"):
            recipient_ids.add(str(entry["id"]))
        for event in entry.get("messaging", []) or []:
            if not isinstance(event, dict):
                continue
            recipient = event.get("recipient") or {}
            if isinstance(recipient, dict) and recipient.get("id"):
                recipient_ids.add(str(recipient["id"]))
    return recipient_ids


def _whatsapp_phone_number_ids(payload: dict[str, Any]) -> set[str]:
    phone_ids: set[str] = set()
    for entry in payload.get("entry", []):
        if not isinstance(entry, dict):
            continue
        for change in entry.get("changes", []) or []:
            if not isinstance(change, dict):
                continue
            value = change.get("value") or {}
            if not isinstance(value, dict):
                continue
            phone_id = (value.get("metadata") or {}).get("phone_number_id")
            if phone_id:
                phone_ids.add(str(phone_id))
    return phone_ids


def _header_value(headers: dict[str, str], name: str) -> str | None:
    return headers.get(name) or headers.get(name.lower())


def _candidate_webhook_accounts(
    db: Session, provider: ChannelProvider, payload: dict[str, Any], headers: dict[str, str]
) -> list[ChannelAccount]:
    stmt = select(ChannelAccount).where(ChannelAccount.provider == provider)
    if provider == ChannelProvider.INSTAGRAM:
        recipient_ids = _instagram_recipient_ids(payload)
        if recipient_ids:
            stmt = stmt.where(ChannelAccount.external_account_id.in_(recipient_ids))
    elif provider == ChannelProvider.WHATSAPP:
        phone_ids = _whatsapp_phone_number_ids(payload)
        if phone_ids:
            stmt = stmt.where(ChannelAccount.phone_number_id.in_(phone_ids))
    elif provider in {ChannelProvider.TELEGRAM, ChannelProvider.BALE, ChannelProvider.RUBIKA}:
        secret = _header_value(headers, "X-Telegram-Bot-Api-Secret-Token") or _header_value(
            headers, "X-Webhook-Secret"
        )
        if not secret:
            return []
        stmt = stmt.where(ChannelAccount.webhook_secret == secret)
    return list(db.scalars(stmt).all())


async def _verified_webhook_account(
    db: Session, provider: ChannelProvider, payload: dict[str, Any], request: Request
) -> ChannelAccount:
    headers = dict(request.headers)
    candidates = _candidate_webhook_accounts(db, provider, payload, headers)
    if not candidates:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No channel account configured for this webhook",
        )
    for account in candidates:
        if not account.webhook_secret:
            continue
        if await _account_adapter(account).verify_webhook(request):
            return account
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail="Invalid webhook signature or secret"
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


@router.post("/shops/{shop_id}/channels", response_model=ChannelAccountRead, status_code=201)
def create_channel_account(
    shop_id: UUID,
    payload: ChannelAccountCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.ADMIN))],
    db: Annotated[Session, Depends(get_db_session)],
) -> ChannelAccountRead:
    ShopService(db).get_shop(shop_id, current_user)
    return ChannelAccountRead.model_validate(ChannelAccountService(db).create(shop_id, payload))


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
    db: Annotated[Session, Depends(get_db_session)],
    hub_mode: Annotated[str | None, Query(alias="hub.mode")] = None,
    hub_verify_token: Annotated[str | None, Query(alias="hub.verify_token")] = None,
    hub_challenge: Annotated[str | None, Query(alias="hub.challenge")] = None,
) -> Response:
    if (
        provider in {ChannelProvider.INSTAGRAM, ChannelProvider.WHATSAPP}
        and hub_mode == "subscribe"
    ):
        if not hub_verify_token:
            return Response(status_code=403)
        account = db.scalar(
            select(ChannelAccount).where(
                ChannelAccount.provider == provider,
                ChannelAccount.webhook_verify_token == hub_verify_token,
            )
        )
        if account:
            return Response(content=hub_challenge or "", media_type="text/plain")
        return Response(status_code=403)
    return Response(content="ok", media_type="text/plain")


@router.post(
    "/channels/{provider}/webhook", response_model=WebhookAckResponse | WebhookIgnoredResponse
)
async def receive_channel_webhook(
    provider: ChannelProvider,
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    _: Annotated[None, Depends(rate_limit_webhook)],
) -> WebhookAckResponse | WebhookIgnoredResponse:
    body = await request.body()
    try:
        payload: dict[str, Any] = json.loads(body.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload"
        ) from exc
    account = await _verified_webhook_account(db, provider, payload, request)
    return ChannelWebhookIngestionService(db).handle_payload(
        provider,
        payload,
        dict(request.headers),
        shop_id=account.shop_id,
        channel_account_id=account.id,
    )


@router.post("/webhooks/{provider}", response_model=WebhookAckResponse | WebhookIgnoredResponse)
async def receive_provider_compat_webhook(
    provider: ChannelProvider,
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    _: Annotated[None, Depends(rate_limit_webhook)],
) -> WebhookAckResponse | WebhookIgnoredResponse:
    return await receive_channel_webhook(provider, request, db, None)
