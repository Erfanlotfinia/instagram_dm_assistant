from __future__ import annotations

import json
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, rate_limit_webhook, require_shop_role
from app.channels.adapters import InstagramProviderAdapter
from app.core.config import get_settings
from app.db.session import get_db_session
from app.domain.enums import ChannelAccountStatus, ChannelProvider, UserRole
from app.domain.models import ChannelAccount, ShopMember, User
from app.schemas.channels import (
    ChannelAccountCreate,
    ChannelAccountCredentials,
    ChannelAccountRead,
    ChannelAccountUpdate,
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


def _default_instagram_webhook_url(channel_account_id: UUID) -> str:
    return (
        f"{get_settings().public_api_base_url}"
        f"/api/v1/channels/instagram/{channel_account_id}/webhook"
    )


def _default_telegram_webhook_url(channel_account_id: UUID) -> str:
    return (
        f"{get_settings().public_api_base_url}"
        f"/api/v1/channels/telegram/{channel_account_id}/webhook"
    )


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
    accounts = db.scalars(
        select(ChannelAccount).where(
            ChannelAccount.provider == ChannelProvider.TELEGRAM,
            ChannelAccount.webhook_secret_encrypted.is_not(None),
        )
    )
    return next(
        (
            account
            for account in accounts
            if adapter_for_provider(ChannelProvider.TELEGRAM, account).webhook_secret == secret
        ),
        None,
    )


def _candidate_webhook_accounts(
    db: Session,
    provider: ChannelProvider,
    payload: dict[str, Any],
    headers: dict[str, str],
    channel_account_id: UUID | None = None,
) -> list[ChannelAccount]:
    stmt = select(ChannelAccount).where(ChannelAccount.provider == provider)
    if channel_account_id:
        stmt = stmt.where(ChannelAccount.id == channel_account_id)
    elif provider == ChannelProvider.INSTAGRAM:
        recipient_ids = _instagram_recipient_ids(payload)
        if recipient_ids:
            stmt = stmt.where(ChannelAccount.external_account_id.in_(recipient_ids))
    elif provider == ChannelProvider.WHATSAPP:
        phone_ids = _whatsapp_phone_number_ids(payload)
        if phone_ids:
            stmt = stmt.where(ChannelAccount.phone_number_id.in_(phone_ids))
    elif provider in {
        ChannelProvider.TELEGRAM,
        ChannelProvider.BALE,
        ChannelProvider.RUBIKA,
    }:
        secret = _header_value(headers, "X-Telegram-Bot-Api-Secret-Token") or _header_value(
            headers, "X-Webhook-Secret"
        )
        if not secret:
            return []
        # Encrypted webhook secrets cannot be queried directly; candidates are
        # compared after decryption by the provider adapter below.
    return list(db.scalars(stmt).all())


async def _verified_webhook_account(
    db: Session,
    provider: ChannelProvider,
    payload: dict[str, Any],
    request: Request,
    channel_account_id: UUID | None = None,
    allow_legacy_meta_secret: bool = False,
) -> ChannelAccount:
    headers = dict(request.headers)
    candidates = _candidate_webhook_accounts(db, provider, payload, headers, channel_account_id)
    if not candidates and channel_account_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel account not found for this webhook",
        )
    if not candidates:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No channel account configured for this webhook",
        )
    if allow_legacy_meta_secret and provider == ChannelProvider.INSTAGRAM:
        settings = get_settings()
        if settings.webhook_signature_bypass:
            return candidates[0]
        if settings.meta_app_secret:
            if await InstagramProviderAdapter(settings.meta_app_secret).verify_webhook(request):
                return candidates[0]
    for account in candidates:
        if not account.webhook_secret_encrypted:
            continue
        if await adapter_for_provider(provider, account).verify_webhook(request):
            return account
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Invalid webhook signature or secret",
    )


@router.get("/shops/{shop_id}/channels", response_model=list[ChannelAccountRead])
def list_channel_accounts(
    shop_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
) -> list[ChannelAccountRead]:
    ShopService(db).get_shop(shop_id, current_user)
    return [
        ChannelAccountRead.from_account(account)
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
    return ChannelAccountRead.from_account(ChannelAccountService(db).create(shop_id, payload))


@router.get(
    "/shops/{shop_id}/channels/{channel_account_id}",
    response_model=ChannelAccountRead,
)
def get_channel_account(
    shop_id: UUID,
    channel_account_id: UUID,
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.OPERATOR))],
    db: Annotated[Session, Depends(get_db_session)],
) -> ChannelAccountRead:
    account = ChannelAccountService(db).get(shop_id, channel_account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Channel account not found")
    return ChannelAccountRead.from_account(account)


@router.patch(
    "/shops/{shop_id}/channels/{channel_account_id}",
    response_model=ChannelAccountRead,
)
def update_channel_account(
    shop_id: UUID,
    channel_account_id: UUID,
    payload: ChannelAccountUpdate,
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.ADMIN))],
    db: Annotated[Session, Depends(get_db_session)],
) -> ChannelAccountRead:
    service = ChannelAccountService(db)
    account = service.get(shop_id, channel_account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Channel account not found")
    return ChannelAccountRead.from_account(service.update(account, payload))


@router.post(
    "/shops/{shop_id}/channels/{channel_account_id}/credentials",
    response_model=ChannelAccountRead,
)
def update_channel_credentials(
    shop_id: UUID,
    channel_account_id: UUID,
    payload: ChannelAccountCredentials,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.ADMIN))],
    db: Annotated[Session, Depends(get_db_session)],
) -> ChannelAccountRead:
    service = ChannelAccountService(db)
    account = service.get(shop_id, channel_account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Channel account not found")
    return ChannelAccountRead.from_account(
        service.save_credentials(account, payload, current_user.id)
    )


@router.post(
    "/shops/{shop_id}/channels/{channel_account_id}/validate",
    response_model=ChannelAccountRead,
)
async def validate_channel_credentials(
    shop_id: UUID,
    channel_account_id: UUID,
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.ADMIN))],
    db: Annotated[Session, Depends(get_db_session)],
) -> ChannelAccountRead:
    service = ChannelAccountService(db)
    account = service.get(shop_id, channel_account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Channel account not found")
    return ChannelAccountRead.from_account(await service.validate(account))


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
    provider: str,
    db: Annotated[Session, Depends(get_db_session)],
    hub_mode: Annotated[str | None, Query(alias="hub.mode")] = None,
    hub_verify_token: Annotated[str | None, Query(alias="hub.verify_token")] = None,
    hub_challenge: Annotated[str | None, Query(alias="hub.challenge")] = None,
) -> Response:
    try:
        provider_enum = ChannelProvider(provider)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Unsupported channel provider") from exc
    if provider_enum in {ChannelProvider.INSTAGRAM, ChannelProvider.WHATSAPP}:
        if hub_mode != "subscribe" or not hub_verify_token:
            raise HTTPException(status_code=403, detail="Verification failed")
    elif not hub_verify_token:
        raise HTTPException(
            status_code=400,
            detail="This provider does not support an unauthenticated challenge",
        )
    account = db.scalar(
        select(ChannelAccount).where(
            ChannelAccount.provider == provider_enum,
            ChannelAccount.webhook_verify_token == hub_verify_token,
        )
    )
    if account is None:
        raise HTTPException(status_code=403, detail="Verification failed")
    return Response(content=hub_challenge or "", media_type="text/plain")


def _get_instagram_webhook_account(
    db: Session, channel_account_id: UUID, hub_verify_token: str | None = None
) -> ChannelAccount:
    account = db.scalar(
        select(ChannelAccount).where(
            ChannelAccount.id == channel_account_id,
            ChannelAccount.provider == ChannelProvider.INSTAGRAM,
        )
    )
    if account is None:
        raise HTTPException(status_code=404, detail="Instagram channel account not found")
    if account.status == ChannelAccountStatus.DISABLED:
        raise HTTPException(status_code=403, detail="Instagram channel account is disabled")
    if hub_verify_token and account.webhook_verify_token != hub_verify_token:
        raise HTTPException(status_code=403, detail="Verification failed")
    return account


@router.get("/channels/instagram/{channel_account_id}/webhook")
def verify_instagram_channel_webhook(
    channel_account_id: UUID,
    db: Annotated[Session, Depends(get_db_session)],
    hub_mode: Annotated[str | None, Query(alias="hub.mode")] = None,
    hub_verify_token: Annotated[str | None, Query(alias="hub.verify_token")] = None,
    hub_challenge: Annotated[str | None, Query(alias="hub.challenge")] = None,
) -> Response:
    if hub_mode != "subscribe" or not hub_verify_token:
        raise HTTPException(status_code=403, detail="Verification failed")
    _get_instagram_webhook_account(db, channel_account_id, hub_verify_token)
    return Response(content=hub_challenge or "", media_type="text/plain")


@router.post(
    "/channels/instagram/{channel_account_id}/webhook",
    response_model=WebhookAckResponse | WebhookIgnoredResponse,
)
async def receive_instagram_channel_webhook(
    channel_account_id: UUID,
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    _: Annotated[None, Depends(rate_limit_webhook)],
) -> WebhookAckResponse | WebhookIgnoredResponse:
    return await _receive_channel_webhook(
        ChannelProvider.INSTAGRAM,
        request,
        db,
        channel_account_id=channel_account_id,
    )


@router.post(
    "/channels/{provider}/webhook",
    response_model=WebhookAckResponse | WebhookIgnoredResponse,
)
async def receive_channel_webhook(
    provider: str,
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    _: Annotated[None, Depends(rate_limit_webhook)],
) -> WebhookAckResponse | WebhookIgnoredResponse:
    try:
        provider_enum = ChannelProvider(provider)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Unsupported channel provider") from exc
    return await _receive_channel_webhook(provider_enum, request, db)


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
    allow_legacy_meta_secret: bool = False,
) -> WebhookAckResponse | WebhookIgnoredResponse:
    body = await request.body()
    try:
        payload: dict[str, Any] = json.loads(body.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload"
        ) from exc
    account = await _verified_webhook_account(
        db,
        provider,
        payload,
        request,
        channel_account_id,
        allow_legacy_meta_secret=allow_legacy_meta_secret,
    )
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
        raise HTTPException(status_code=404, detail="Telegram channel account not found")
    return await adapter_for_provider(ChannelProvider.TELEGRAM, account).configure_webhook(
        payload.get("url") or _default_telegram_webhook_url(account.id),
        adapter_for_provider(ChannelProvider.TELEGRAM, account).webhook_secret,
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
        raise HTTPException(status_code=404, detail="Telegram channel account not found")
    return await adapter_for_provider(ChannelProvider.TELEGRAM, account).delete_webhook()


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
        raise HTTPException(status_code=404, detail="Telegram channel account not found")
    return await adapter_for_provider(ChannelProvider.TELEGRAM, account).get_webhook_info()
