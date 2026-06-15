from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.request_context import get_request_context
from app.domain.models import AdminAuditLog
from app.repositories.audit_log_repository import AuditLogRepository


class AuditService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = AuditLogRepository(db)

    def log(
        self,
        *,
        action: str,
        entity_type: str,
        shop_id: UUID | None = None,
        actor_user_id: UUID | None = None,
        entity_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AdminAuditLog:
        ctx = get_request_context()
        resolved_ip = ip_address or (ctx.ip_address if ctx else None)
        resolved_ua = user_agent or (ctx.user_agent if ctx else None)

        entry = AdminAuditLog(
            shop_id=shop_id,
            user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=metadata or {},
            ip_address=resolved_ip,
            user_agent=resolved_ua,
        )
        return self.repo.create(entry)

    def commit(self) -> None:
        self.db.commit()
