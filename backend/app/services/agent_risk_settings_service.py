from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.models import ShopAgentSettings


class AgentRiskSettingsService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_or_create(self, shop_id: UUID) -> ShopAgentSettings:
        settings = self.db.get(ShopAgentSettings, shop_id)
        if settings is None:
            settings = ShopAgentSettings(shop_id=shop_id)
            self.db.add(settings)
            self.db.flush()
        return settings
