from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.domain.models import RefreshSession


def hash_token(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def fingerprint(value: str | None) -> str | None:
    return hash_token(value) if value else None


class SessionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, user_id: UUID, user_agent: str | None, ip: str | None) -> tuple[RefreshSession, str]:
        token = secrets.token_urlsafe(48)
        session = RefreshSession(
            user_id=user_id,
            session_id=secrets.token_urlsafe(24),
            refresh_token_hash=hash_token(token),
            expires_at=datetime.now(UTC) + timedelta(days=get_settings().refresh_token_expire_days),
            user_agent_hash=fingerprint(user_agent),
            ip_hash=fingerprint(ip),
            family_id=uuid4(),
            parent_session_id=None,
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session, token

    def rotate(self, refresh_token: str, user_agent: str | None, ip: str | None) -> tuple[RefreshSession, str] | None:
        now = datetime.now(UTC)
        session = self.db.query(RefreshSession).filter_by(refresh_token_hash=hash_token(refresh_token)).first()
        if session is None:
            return None
        if session.revoked_at is not None:
            self.revoke_family(session.family_id)
            return None
        if session.expires_at <= now:
            session.revoked_at = now
            self.db.commit()
            return None
        session.revoked_at = now
        token = secrets.token_urlsafe(48)
        new_session = RefreshSession(
            user_id=session.user_id,
            session_id=secrets.token_urlsafe(24),
            refresh_token_hash=hash_token(token),
            expires_at=now + timedelta(days=get_settings().refresh_token_expire_days),
            user_agent_hash=fingerprint(user_agent),
            ip_hash=fingerprint(ip),
            family_id=session.family_id,
            parent_session_id=session.session_id,
        )
        self.db.add(new_session)
        self.db.commit()
        self.db.refresh(new_session)
        return new_session, token

    def revoke_by_token(self, refresh_token: str | None) -> None:
        if not refresh_token:
            return
        session = self.db.query(RefreshSession).filter_by(refresh_token_hash=hash_token(refresh_token)).first()
        if session and session.revoked_at is None:
            session.revoked_at = datetime.now(UTC)
            self.db.commit()

    def revoke_family(self, family_id: UUID) -> None:
        now = datetime.now(UTC)
        self.db.query(RefreshSession).filter_by(family_id=family_id, revoked_at=None).update({"revoked_at": now})
        self.db.commit()
