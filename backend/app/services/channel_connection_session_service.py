from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.domain.enums import (
    ChannelConnectionMethod,
    ChannelConnectionProvider,
    ChannelConnectionSessionStatus,
)
from app.domain.models import ChannelConnectionSession
from app.repositories.channel_connection_session_repository import (
    ChannelConnectionSessionRepository,
)

SESSION_TTL_MINUTES = 30
TERMINAL_STATUSES = {
    ChannelConnectionSessionStatus.CONNECTED,
    ChannelConnectionSessionStatus.FAILED,
    ChannelConnectionSessionStatus.EXPIRED,
    ChannelConnectionSessionStatus.CANCELLED,
}


class ChannelConnectionSessionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = ChannelConnectionSessionRepository(db)
        self.settings = get_settings()

    def create_instagram_session(
        self,
        *,
        shop_id: UUID,
        created_by: UUID,
        reconnect_channel_account_id: UUID | None = None,
    ) -> ChannelConnectionSession:
        self.repo.expire_stale_sessions()
        payload: dict[str, str] | None = None
        if reconnect_channel_account_id:
            payload = {"reconnect_channel_account_id": str(reconnect_channel_account_id)}
        session = ChannelConnectionSession(
            shop_id=shop_id,
            provider=ChannelConnectionProvider.INSTAGRAM,
            method=ChannelConnectionMethod.META_OAUTH_BUSINESS_LOGIN,
            status=ChannelConnectionSessionStatus.PENDING,
            state=secrets.token_urlsafe(32),
            nonce=secrets.token_urlsafe(32),
            redirect_uri=self.settings.meta_oauth_redirect_uri,
            requested_scopes_json=self.settings.meta_oauth_scopes,
            provider_payload_redacted=payload,
            created_by=created_by,
            expires_at=datetime.now(UTC) + timedelta(minutes=SESSION_TTL_MINUTES),
        )
        return self.repo.create(session)

    def mark_redirected(self, session: ChannelConnectionSession) -> ChannelConnectionSession:
        session.status = ChannelConnectionSessionStatus.REDIRECTED
        return self.repo.save(session)

    def get_valid_by_state(self, state: str) -> ChannelConnectionSession:
        self.repo.expire_stale_sessions()
        session = self.repo.get_by_state(state)
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid OAuth state",
            )
        if session.status in TERMINAL_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OAuth state has already been used",
            )
        if session.expires_at < datetime.now(UTC):
            session.status = ChannelConnectionSessionStatus.EXPIRED
            session.oauth_token_encrypted = None
            self.repo.save(session)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OAuth session expired",
            )
        return session

    def get_for_shop(self, shop_id: UUID, session_id: UUID) -> ChannelConnectionSession:
        self.repo.expire_stale_sessions()
        session = self.repo.get_for_shop(shop_id, session_id)
        if session is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        return session

    def assert_session_actionable(self, session: ChannelConnectionSession) -> None:
        if session.shop_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid session")
        if session.status in TERMINAL_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session is no longer active",
            )
        if session.expires_at < datetime.now(UTC):
            session.status = ChannelConnectionSessionStatus.EXPIRED
            session.oauth_token_encrypted = None
            self.repo.save(session)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OAuth session expired",
            )

    def complete_session(
        self,
        session: ChannelConnectionSession,
        *,
        status: ChannelConnectionSessionStatus,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> ChannelConnectionSession:
        session.status = status
        session.completed_at = datetime.now(UTC)
        session.error_code = error_code
        session.error_message = error_message
        if status in TERMINAL_STATUSES:
            session.oauth_token_encrypted = None
        return self.repo.save(session)
