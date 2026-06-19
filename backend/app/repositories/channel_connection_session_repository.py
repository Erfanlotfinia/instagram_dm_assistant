from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import ChannelConnectionSessionStatus
from app.domain.models import ChannelConnectionSession


class ChannelConnectionSessionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, session: ChannelConnectionSession) -> ChannelConnectionSession:
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_by_id(self, session_id: UUID) -> ChannelConnectionSession | None:
        return self.db.get(ChannelConnectionSession, session_id)

    def get_for_shop(self, shop_id: UUID, session_id: UUID) -> ChannelConnectionSession | None:
        return self.db.scalar(
            select(ChannelConnectionSession).where(
                ChannelConnectionSession.id == session_id,
                ChannelConnectionSession.shop_id == shop_id,
            )
        )

    def get_by_state(self, state: str) -> ChannelConnectionSession | None:
        return self.db.scalar(
            select(ChannelConnectionSession).where(ChannelConnectionSession.state == state)
        )

    def save(self, session: ChannelConnectionSession) -> ChannelConnectionSession:
        self.db.commit()
        self.db.refresh(session)
        return session

    def expire_stale_sessions(self, now: datetime | None = None) -> int:
        current = now or datetime.now(UTC)
        sessions = list(
            self.db.scalars(
                select(ChannelConnectionSession).where(
                    ChannelConnectionSession.expires_at < current,
                    ChannelConnectionSession.status.in_(
                        [
                            ChannelConnectionSessionStatus.PENDING,
                            ChannelConnectionSessionStatus.REDIRECTED,
                            ChannelConnectionSessionStatus.AUTHORIZED,
                            ChannelConnectionSessionStatus.ACCOUNT_SELECTION_REQUIRED,
                        ]
                    ),
                )
            ).all()
        )
        for session in sessions:
            session.status = ChannelConnectionSessionStatus.EXPIRED
            session.oauth_token_encrypted = None
        if sessions:
            self.db.commit()
        return len(sessions)
