from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_shop_role
from app.db.session import get_db_session
from app.domain.enums import ChannelProvider, UserRole
from app.domain.models import ChannelAccount, ShopMember, TelegramConnectionSession, User
from app.schemas.channels import ChannelAccountRead
from app.schemas.telegram_connect import (
    TelegramConnectBotTokenRequest,
    TelegramConnectSessionRead,
    TelegramConnectStartRequest,
    TelegramConnectStartResponse,
)
from app.services.channel_account_service import ChannelAccountService
from app.services.shop_service import ShopService
from app.services.telegram_business_connection_service import TelegramBusinessConnectionService
from app.services.telegram_connect_service import TelegramConnectService
from app.services.telegram_managed_bot_service import TelegramManagedBotService

router = APIRouter(tags=["telegram-connect"])


def _session_read(
    session: TelegramConnectionSession, account: ChannelAccount | None = None
) -> TelegramConnectSessionRead:
    metadata = session.metadata_json or {}
    return TelegramConnectSessionRead(
        id=session.id,
        shop_id=session.shop_id,
        mode=session.mode,
        status=session.status,
        expires_at=session.expires_at,
        completed_at=session.completed_at,
        error_message=session.error_message,
        channel_account_id=session.channel_account_id,
        bot_username=account.bot_username if account else metadata.get("bot_username"),
        bot_id=account.bot_id if account else metadata.get("bot_id"),
        telegram_business_enabled=bool(account.telegram_business_enabled) if account else False,
        deep_link=metadata.get("deep_link"),
        suggested_bot_username=metadata.get("suggested_bot_username"),
        managed_bot=bool(metadata.get("managed_bot")),
        metadata_json=metadata,
    )


@router.post(
    "/shops/{shop_id}/channels/telegram/connect/start",
    response_model=TelegramConnectStartResponse,
)
async def start_telegram_connect(
    shop_id: UUID,
    payload: TelegramConnectStartRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.ADMIN))],
    db: Annotated[Session, Depends(get_db_session)],
) -> TelegramConnectStartResponse:
    ShopService(db).get_shop(shop_id, current_user)
    if payload.managed_bot:
        session = await TelegramManagedBotService(db).start_managed_session(
            shop_id=shop_id,
            created_by=current_user.id,
            display_name=payload.display_name,
            channel_account_id=payload.channel_account_id,
        )
        metadata = session.metadata_json or {}
        return TelegramConnectStartResponse(
            session_id=session.id,
            expires_at=session.expires_at,
            status=session.status,
            deep_link=metadata.get("deep_link"),
            suggested_bot_username=metadata.get("suggested_bot_username"),
            managed_bot=True,
        )
    session = TelegramConnectService(db).start_session(
        shop_id=shop_id,
        created_by=current_user.id,
        mode=payload.mode,
        display_name=payload.display_name,
        channel_account_id=payload.channel_account_id,
    )
    return TelegramConnectStartResponse(
        session_id=session.id,
        expires_at=session.expires_at,
        status=session.status,
    )


@router.get(
    "/shops/{shop_id}/channels/telegram/connect/{session_id}",
    response_model=TelegramConnectSessionRead,
)
def get_telegram_connect_session(
    shop_id: UUID,
    session_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.ADMIN))],
    db: Annotated[Session, Depends(get_db_session)],
) -> TelegramConnectSessionRead:
    ShopService(db).get_shop(shop_id, current_user)
    session = TelegramConnectService(db).get_session(shop_id, session_id)
    account = None
    if session.channel_account_id:
        account = ChannelAccountService(db).get(shop_id, session.channel_account_id)
    return _session_read(session, account)


@router.post(
    "/shops/{shop_id}/channels/telegram/connect/{session_id}/bot-token",
    response_model=TelegramConnectSessionRead,
)
async def submit_telegram_bot_token(
    shop_id: UUID,
    session_id: UUID,
    payload: TelegramConnectBotTokenRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.ADMIN))],
    db: Annotated[Session, Depends(get_db_session)],
) -> TelegramConnectSessionRead:
    ShopService(db).get_shop(shop_id, current_user)
    session = await TelegramConnectService(db).submit_bot_token(
        shop_id,
        session_id,
        payload.bot_token,
        payload.webhook_secret,
        current_user.id,
    )
    account = None
    if session.channel_account_id:
        account = ChannelAccountService(db).get(shop_id, session.channel_account_id)
    return _session_read(session, account)


@router.post(
    "/shops/{shop_id}/channels/telegram/connect/{session_id}/complete",
    response_model=ChannelAccountRead,
)
async def complete_telegram_connect(
    shop_id: UUID,
    session_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.ADMIN))],
    db: Annotated[Session, Depends(get_db_session)],
) -> ChannelAccountRead:
    ShopService(db).get_shop(shop_id, current_user)
    account = await TelegramConnectService(db).complete_session(
        shop_id, session_id, current_user.id
    )
    return ChannelAccountRead.from_account(account)


@router.post(
    "/shops/{shop_id}/channels/telegram/connect/{session_id}/cancel",
    response_model=TelegramConnectSessionRead,
)
async def cancel_telegram_connect(
    shop_id: UUID,
    session_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.ADMIN))],
    db: Annotated[Session, Depends(get_db_session)],
) -> TelegramConnectSessionRead:
    ShopService(db).get_shop(shop_id, current_user)
    session = await TelegramConnectService(db).cancel_session(
        shop_id, session_id, current_user.id
    )
    return _session_read(session)


def _get_telegram_account(
    db: Session, shop_id: UUID, channel_account_id: UUID
) -> ChannelAccount:
    from fastapi import HTTPException, status

    account = ChannelAccountService(db).get(shop_id, channel_account_id)
    if account is None or account.provider != ChannelProvider.TELEGRAM:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Telegram account not found")
    return account


@router.post(
    "/shops/{shop_id}/channels/{channel_account_id}/telegram/business/sync",
    response_model=ChannelAccountRead,
)
async def sync_telegram_business(
    shop_id: UUID,
    channel_account_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.ADMIN))],
    db: Annotated[Session, Depends(get_db_session)],
) -> ChannelAccountRead:
    ShopService(db).get_shop(shop_id, current_user)
    account = _get_telegram_account(db, shop_id, channel_account_id)
    await TelegramBusinessConnectionService(db).sync(account)
    db.refresh(account)
    return ChannelAccountRead.from_account(account)


@router.post(
    "/shops/{shop_id}/channels/{channel_account_id}/telegram/business/refresh",
    response_model=ChannelAccountRead,
)
async def refresh_telegram_business(
    shop_id: UUID,
    channel_account_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.ADMIN))],
    db: Annotated[Session, Depends(get_db_session)],
) -> ChannelAccountRead:
    ShopService(db).get_shop(shop_id, current_user)
    account = _get_telegram_account(db, shop_id, channel_account_id)
    account = await TelegramBusinessConnectionService(db).refresh(account)
    return ChannelAccountRead.from_account(account)


@router.post(
    "/shops/{shop_id}/channels/{channel_account_id}/telegram/business/validate",
    response_model=ChannelAccountRead,
)
async def validate_telegram_business(
    shop_id: UUID,
    channel_account_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.ADMIN))],
    db: Annotated[Session, Depends(get_db_session)],
) -> ChannelAccountRead:
    from datetime import UTC, datetime

    ShopService(db).get_shop(shop_id, current_user)
    account = _get_telegram_account(db, shop_id, channel_account_id)
    valid = await TelegramBusinessConnectionService(db).validate(account)
    account.last_validation_at = datetime.now(UTC)
    account.last_error = None if valid else "Telegram business validation failed"
    db.commit()
    db.refresh(account)
    return ChannelAccountRead.from_account(account)


@router.post(
    "/shops/{shop_id}/channels/{channel_account_id}/telegram/business/reconnect",
    response_model=TelegramConnectStartResponse,
)
def reconnect_telegram_business(
    shop_id: UUID,
    channel_account_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.ADMIN))],
    db: Annotated[Session, Depends(get_db_session)],
) -> TelegramConnectStartResponse:
    ShopService(db).get_shop(shop_id, current_user)
    account = _get_telegram_account(db, shop_id, channel_account_id)
    from app.domain.enums import TelegramConnectionMode

    session = TelegramConnectService(db).start_session(
        shop_id=shop_id,
        created_by=current_user.id,
        mode=account.connection_mode or TelegramConnectionMode.BUSINESS,
        display_name=account.display_name,
        channel_account_id=account.id,
    )
    return TelegramConnectStartResponse(
        session_id=session.id,
        expires_at=session.expires_at,
        status=session.status,
    )


@router.post(
    "/shops/{shop_id}/channels/{channel_account_id}/telegram/managed-bot/rotate-token",
    response_model=ChannelAccountRead,
)
async def rotate_telegram_managed_bot_token(
    shop_id: UUID,
    channel_account_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.ADMIN))],
    db: Annotated[Session, Depends(get_db_session)],
) -> ChannelAccountRead:
    ShopService(db).get_shop(shop_id, current_user)
    _get_telegram_account(db, shop_id, channel_account_id)
    account = await TelegramManagedBotService(db).rotate_token(
        shop_id, channel_account_id, current_user.id
    )
    return ChannelAccountRead.from_account(account)


@router.post(
    "/shops/{shop_id}/channels/{channel_account_id}/telegram/managed-bot/reconnect",
    response_model=ChannelAccountRead,
)
async def reconnect_telegram_managed_bot(
    shop_id: UUID,
    channel_account_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.ADMIN))],
    db: Annotated[Session, Depends(get_db_session)],
) -> ChannelAccountRead:
    ShopService(db).get_shop(shop_id, current_user)
    _get_telegram_account(db, shop_id, channel_account_id)
    account = await TelegramManagedBotService(db).reconnect_managed_bot(
        shop_id, channel_account_id, current_user.id
    )
    return ChannelAccountRead.from_account(account)
