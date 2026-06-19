from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_shop_role
from app.core.config import get_settings
from app.core.security import decrypt_secret, encrypt_secret
from app.db.session import get_db_session
from app.domain.enums import (
    ChannelConnectionSessionStatus,
    ChannelProvider,
    UserRole,
)
from app.domain.models import ChannelConnectionSession, ShopMember, User
from app.schemas.channels import ChannelAccountRead
from app.schemas.instagram_connect import (
    InstagramConnectSessionRead,
    InstagramConnectStartResponse,
    InstagramCandidateAccountRead,
    InstagramReadinessRead,
    InstagramSelectAccountRequest,
)
from app.services.channel_account_service import ChannelAccountService
from app.services.channel_connection_session_service import ChannelConnectionSessionService
from app.services.instagram_meta_connect_service import (
    InstagramCandidateAccount,
    InstagramMetaConnectError,
    InstagramMetaConnectService,
)
from app.services.shop_service import ShopService

router = APIRouter(tags=["instagram-connect"])


def _frontend_redirect(path: str) -> RedirectResponse:
    base = get_settings().frontend_base_url.rstrip("/")
    return RedirectResponse(url=f"{base}{path}", status_code=status.HTTP_302_FOUND)


def _session_read(session: ChannelConnectionSession) -> InstagramConnectSessionRead:
    payload = session.provider_payload_redacted or {}
    candidates = [
        InstagramCandidateAccountRead.model_validate(item)
        for item in payload.get("candidates", [])
        if isinstance(item, dict)
    ]
    channel_account_id = payload.get("channel_account_id")
    return InstagramConnectSessionRead(
        id=session.id,
        shop_id=session.shop_id,
        status=session.status,
        expires_at=session.expires_at,
        completed_at=session.completed_at,
        error_code=session.error_code,
        error_message=session.error_message,
        candidate_accounts=candidates,
        channel_account_id=UUID(channel_account_id) if channel_account_id else None,
    )


@router.post(
    "/shops/{shop_id}/channels/instagram/connect/start",
    response_model=InstagramConnectStartResponse,
)
def start_instagram_connect(
    shop_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.ADMIN))],
    db: Annotated[Session, Depends(get_db_session)],
) -> InstagramConnectStartResponse:
    ShopService(db).get_shop(shop_id, current_user)
    session_service = ChannelConnectionSessionService(db)
    meta_service = InstagramMetaConnectService(db)
    session = session_service.create_instagram_session(shop_id=shop_id, created_by=current_user.id)
    authorization_url = meta_service.build_authorization_url(session)
    session_service.mark_redirected(session)
    return InstagramConnectStartResponse(
        authorization_url=authorization_url,
        session_id=session.id,
        expires_at=session.expires_at,
    )


@router.get("/channels/instagram/oauth/callback")
async def instagram_oauth_callback(
    db: Annotated[Session, Depends(get_db_session)],
    code: Annotated[str | None, Query()] = None,
    state: Annotated[str | None, Query()] = None,
    error: Annotated[str | None, Query()] = None,
    error_reason: Annotated[str | None, Query(alias="error_reason")] = None,
    error_description: Annotated[str | None, Query(alias="error_description")] = None,
) -> RedirectResponse:
    session_service = ChannelConnectionSessionService(db)
    meta_service = InstagramMetaConnectService(db)

    if error or not code or not state:
        return _frontend_redirect(
            "/system/channels/instagram/connect?status=failed&error=token_exchange_failed"
        )

    try:
        session = session_service.get_valid_by_state(state)
    except HTTPException:
        return _frontend_redirect(
            "/system/channels/instagram/connect?status=failed&error=connection_expired"
        )

    try:
        short_lived = await meta_service.exchange_code_for_token(code, session.redirect_uri)
        long_lived = await meta_service.exchange_for_long_lived_token(short_lived.access_token)
        missing = await meta_service.validate_required_permissions(long_lived.access_token)
        if missing:
            raise InstagramMetaConnectError(
                "missing_permissions",
                InstagramMetaConnectService.ERROR_MESSAGES["missing_permissions"],
            )

        session.oauth_token_encrypted = encrypt_secret(long_lived.access_token)
        session.status = ChannelConnectionSessionStatus.AUTHORIZED
        db.commit()

        pages = await meta_service.fetch_user_pages(long_lived.access_token)
        candidates = meta_service.extract_candidate_accounts(pages)
        if not candidates:
            session_service.complete_session(
                session,
                status=ChannelConnectionSessionStatus.FAILED,
                error_code="no_business_account",
                error_message=InstagramMetaConnectService.ERROR_MESSAGES["no_business_account"],
            )
            return _frontend_redirect(
                f"/system/channels/instagram/connect?session_id={session.id}&status=failed&error=no_business_account"
            )

        token_expires_at = meta_service.token_expires_at_from_result(long_lived)
        reconnect_id = (session.provider_payload_redacted or {}).get("reconnect_channel_account_id")

        if len(candidates) == 1:
            candidate = candidates[0]
            page_token = meta_service.resolve_page_access_token(pages, candidate)
            if not page_token:
                session_service.complete_session(
                    session,
                    status=ChannelConnectionSessionStatus.FAILED,
                    error_code="no_page_connected",
                    error_message=InstagramMetaConnectService.ERROR_MESSAGES["no_page_connected"],
                )
                return _frontend_redirect(
                    f"/system/channels/instagram/connect?session_id={session.id}&status=failed&error=no_page_connected"
                )
            account = await meta_service.create_or_update_channel_account(
                shop_id=session.shop_id,
                candidate=candidate,
                page_access_token=page_token,
                user_token_scopes=long_lived.scopes,
                token_expires_at=token_expires_at,
                existing_account_id=UUID(reconnect_id) if reconnect_id else None,
            )
            payload = dict(session.provider_payload_redacted or {})
            payload["channel_account_id"] = str(account.id)
            session.provider_payload_redacted = payload
            session.selected_page_id = candidate.page_id
            session.selected_instagram_business_account_id = candidate.instagram_business_account_id
            session.selected_external_account_id = candidate.instagram_business_account_id
            session_service.complete_session(session, status=ChannelConnectionSessionStatus.CONNECTED)
            return _frontend_redirect(
                f"/system/channels/instagram/connect?session_id={session.id}&status=connected"
            )

        session.provider_payload_redacted = {
            **(session.provider_payload_redacted or {}),
            "candidates": meta_service.redact_candidate_accounts(candidates),
        }
        session.status = ChannelConnectionSessionStatus.ACCOUNT_SELECTION_REQUIRED
        db.commit()
        return _frontend_redirect(f"/system/channels/instagram/select?session_id={session.id}")

    except InstagramMetaConnectError as exc:
        session_service.complete_session(
            session,
            status=ChannelConnectionSessionStatus.FAILED,
            error_code=exc.code,
            error_message=exc.message,
        )
        return _frontend_redirect(
            f"/system/channels/instagram/connect?session_id={session.id}&status=failed&error={exc.code}"
        )
    except HTTPException as exc:
        session_service.complete_session(
            session,
            status=ChannelConnectionSessionStatus.FAILED,
            error_code="token_exchange_failed",
            error_message=str(exc.detail),
        )
        return _frontend_redirect(
            f"/system/channels/instagram/connect?session_id={session.id}&status=failed&error=token_exchange_failed"
        )


@router.get(
    "/shops/{shop_id}/channels/instagram/connect/sessions/{session_id}",
    response_model=InstagramConnectSessionRead,
)
def get_instagram_connect_session(
    shop_id: UUID,
    session_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
) -> InstagramConnectSessionRead:
    ShopService(db).get_shop(shop_id, current_user)
    session = ChannelConnectionSessionService(db).get_for_shop(shop_id, session_id)
    return _session_read(session)


@router.post(
    "/shops/{shop_id}/channels/instagram/connect/sessions/{session_id}/select-account",
    response_model=ChannelAccountRead,
)
async def select_instagram_account(
    shop_id: UUID,
    session_id: UUID,
    payload: InstagramSelectAccountRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.ADMIN))],
    db: Annotated[Session, Depends(get_db_session)],
) -> ChannelAccountRead:
    ShopService(db).get_shop(shop_id, current_user)
    session_service = ChannelConnectionSessionService(db)
    meta_service = InstagramMetaConnectService(db)
    session = session_service.get_for_shop(shop_id, session_id)
    session_service.assert_session_actionable(session)
    if session.status != ChannelConnectionSessionStatus.ACCOUNT_SELECTION_REQUIRED:
        raise HTTPException(status_code=400, detail="Account selection is not required for this session")
    if not session.oauth_token_encrypted:
        raise HTTPException(status_code=400, detail="OAuth session is missing authorization context")

    user_token = decrypt_secret(session.oauth_token_encrypted)
    pages = await meta_service.fetch_user_pages(user_token)
    candidates = meta_service.extract_candidate_accounts(pages)
    candidate = next(
        (
            item
            for item in candidates
            if item.page_id == payload.page_id
            and item.instagram_business_account_id == payload.instagram_business_account_id
        ),
        None,
    )
    if candidate is None:
        raise HTTPException(status_code=400, detail="Selected Instagram account is not available")

    page_token = meta_service.resolve_page_access_token(pages, candidate)
    if not page_token:
        raise HTTPException(status_code=400, detail="Could not resolve page access token for selection")

    reconnect_id = (session.provider_payload_redacted or {}).get("reconnect_channel_account_id")
    account = await meta_service.create_or_update_channel_account(
        shop_id=shop_id,
        candidate=candidate,
        page_access_token=page_token,
        user_token_scopes=session.requested_scopes_json,
        token_expires_at=None,
        existing_account_id=UUID(reconnect_id) if reconnect_id else None,
    )
    session.selected_page_id = candidate.page_id
    session.selected_instagram_business_account_id = candidate.instagram_business_account_id
    session.selected_external_account_id = candidate.instagram_business_account_id
    payload_data = dict(session.provider_payload_redacted or {})
    payload_data["channel_account_id"] = str(account.id)
    session.provider_payload_redacted = payload_data
    session_service.complete_session(session, status=ChannelConnectionSessionStatus.CONNECTED)
    return ChannelAccountRead.from_account(account)


@router.post(
    "/shops/{shop_id}/channels/{channel_account_id}/instagram/reconnect",
    response_model=InstagramConnectStartResponse,
)
def reconnect_instagram(
    shop_id: UUID,
    channel_account_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.ADMIN))],
    db: Annotated[Session, Depends(get_db_session)],
) -> InstagramConnectStartResponse:
    ShopService(db).get_shop(shop_id, current_user)
    account = ChannelAccountService(db).get(shop_id, channel_account_id)
    if not account or account.provider != ChannelProvider.INSTAGRAM:
        raise HTTPException(status_code=404, detail="Instagram channel account not found")

    session_service = ChannelConnectionSessionService(db)
    meta_service = InstagramMetaConnectService(db)
    session = session_service.create_instagram_session(
        shop_id=shop_id,
        created_by=current_user.id,
        reconnect_channel_account_id=channel_account_id,
    )
    authorization_url = meta_service.build_authorization_url(session)
    session_service.mark_redirected(session)
    return InstagramConnectStartResponse(
        authorization_url=authorization_url,
        session_id=session.id,
        expires_at=session.expires_at,
    )


@router.post(
    "/shops/{shop_id}/channels/{channel_account_id}/disconnect",
    response_model=ChannelAccountRead,
)
async def disconnect_channel_account(
    shop_id: UUID,
    channel_account_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.ADMIN))],
    db: Annotated[Session, Depends(get_db_session)],
) -> ChannelAccountRead:
    ShopService(db).get_shop(shop_id, current_user)
    service = ChannelAccountService(db)
    account = service.get(shop_id, channel_account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Channel account not found")
    return ChannelAccountRead.from_account(await service.disconnect(account, current_user.id))


@router.get(
    "/shops/{shop_id}/channels/instagram/readiness",
    response_model=InstagramReadinessRead,
)
async def instagram_readiness(
    shop_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.ADMIN))],
    db: Annotated[Session, Depends(get_db_session)],
) -> InstagramReadinessRead:
    ShopService(db).get_shop(shop_id, current_user)
    settings = get_settings()
    webhook_callback_url = (
        f"{settings.public_api_base_url.rstrip('/')}/api/v1/channels/instagram/webhook"
    )
    reachable = False
    try:
        import httpx

        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(webhook_callback_url, params={"hub.mode": "subscribe"})
            reachable = response.status_code in {200, 400, 403}
    except Exception:
        reachable = False

    return InstagramReadinessRead(
        meta_app_id_configured=bool(settings.meta_app_id),
        meta_app_secret_configured=bool(settings.meta_app_secret),
        oauth_redirect_uri=settings.meta_oauth_redirect_uri,
        data_deletion_callback_configured=False,
        privacy_policy_url=settings.meta_privacy_policy_url or None,
        required_scopes=settings.meta_oauth_scopes,
        app_mode="development" if settings.app_env in {"local", "development", "test"} else "live",
        webhook_callback_reachable=reachable,
        webhook_callback_url=webhook_callback_url,
        app_review_status="manual_check_required",
    )
