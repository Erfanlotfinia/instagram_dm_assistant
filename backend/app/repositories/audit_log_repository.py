from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.models import AdminAuditLog


class AuditLogRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, log: AdminAuditLog) -> AdminAuditLog:
        self.db.add(log)
        self.db.flush()
        return log

    def list_for_entity(self, shop_id: UUID, entity_type: str, entity_id: str) -> list[AdminAuditLog]:
        from sqlalchemy import select

        stmt = (
            select(AdminAuditLog)
            .where(
                AdminAuditLog.shop_id == shop_id,
                AdminAuditLog.entity_type == entity_type,
                AdminAuditLog.entity_id == entity_id,
            )
            .order_by(AdminAuditLog.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())
