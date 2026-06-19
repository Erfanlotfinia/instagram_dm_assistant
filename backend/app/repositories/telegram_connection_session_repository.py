from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import TelegramConnectionSessionStatus
from app.domain.models import TelegramConnectionSession


class TelegramConnectionSessionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, session: TelegramConnectionSession) -> TelegramConnectionSession:
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_by_id(self, session_id: UUID) -> TelegramConnectionSession | None:
        return self.db.get(TelegramConnectionSession, session_id)

    def get_for_shop(self, shop_id: UUID, session_id: UUID) -> TelegramConnectionSession | None:
        return self.db.scalar(
            select(TelegramConnectionSession).where(
                TelegramConnectionSession.id == session_id,
                TelegramConnectionSession.shop_id == shop_id,
            )
        )

    def get_by_state(self, state: str) -> TelegramConnectionSession | None:
        return self.db.scalar(
            select(TelegramConnectionSession).where(TelegramConnectionSession.state == state)
        )

    def get_waiting_business_for_account(
        self, channel_account_id: UUID
    ) -> TelegramConnectionSession | None:
        return self.db.scalar(
            select(TelegramConnectionSession).where(
                TelegramConnectionSession.channel_account_id == channel_account_id,
                TelegramConnectionSession.status
                == TelegramConnectionSessionStatus.WAITING_BUSINESS_CONNECTION,
            )
        )

    def save(self, session: TelegramConnectionSession) -> TelegramConnectionSession:
        self.db.commit()
        self.db.refresh(session)
        return session

    def expire_stale(self) -> int:
        current = datetime.now(UTC)
        sessions = list(
            self.db.scalars(
                select(TelegramConnectionSession).where(
                    TelegramConnectionSession.expires_at < current,
                    TelegramConnectionSession.status.in_(
                        [
                            TelegramConnectionSessionStatus.PENDING,
                            TelegramConnectionSessionStatus.WAITING_BOT_TOKEN,
                            TelegramConnectionSessionStatus.WAITING_MANAGED_BOT_APPROVAL,
                            TelegramConnectionSessionStatus.WAITING_BUSINESS_CONNECTION,
                        ]
                    ),
                )
            ).all()
        )
        for session in sessions:
            session.status = TelegramConnectionSessionStatus.EXPIRED
        if sessions:
            self.db.commit()
        return len(sessions)

    @staticmethod
    def new_state() -> str:
        return uuid4().hex
