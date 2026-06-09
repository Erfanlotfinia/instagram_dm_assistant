from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models import PolicyVersion


class PolicyVersionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_active(self, shop_id: UUID) -> PolicyVersion | None:
        return self.db.scalar(
            select(PolicyVersion)
            .where(PolicyVersion.shop_id == shop_id, PolicyVersion.is_active.is_(True))
            .order_by(PolicyVersion.created_at.desc())
            .limit(1)
        )

    def get_by_id(self, shop_id: UUID, policy_version_id: UUID) -> PolicyVersion | None:
        return self.db.scalar(
            select(PolicyVersion).where(
                PolicyVersion.id == policy_version_id,
                PolicyVersion.shop_id == shop_id,
            )
        )

    def ensure_default(self, shop_id: UUID, *, version: str, name: str, config_json: dict) -> PolicyVersion:
        existing = self.db.scalar(
            select(PolicyVersion).where(PolicyVersion.shop_id == shop_id, PolicyVersion.version == version)
        )
        if existing is not None:
            return existing
        policy = PolicyVersion(
            shop_id=shop_id,
            version=version,
            name=name,
            config_json=config_json,
            is_active=True,
        )
        self.db.add(policy)
        self.db.flush()
        return policy
