from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.domain.enums import ResolverConfidenceBand
from app.repositories.shop_repository import ShopRepository
from app.schemas.resolve import ResolverConfidenceThresholds


class ResolverConfidenceService:
    """Map resolver scores to confidence bands with per-tenant thresholds."""

    DEFAULT_KEY = "catalog_intelligence"

    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.shops = ShopRepository(db)

    def thresholds_for_shop(self, shop_id: UUID) -> ResolverConfidenceThresholds:
        shop = self.shops.get_by_id(shop_id)
        stored = {}
        if shop and isinstance(shop.agent_settings, dict):
            stored = shop.agent_settings.get(self.DEFAULT_KEY, {}).get("confidence_thresholds", {})
        return ResolverConfidenceThresholds(
            high=float(stored.get("high", self.settings.resolver_default_high_threshold)),
            medium=float(stored.get("medium", self.settings.resolver_default_medium_threshold)),
        )

    def band_for_score(self, shop_id: UUID, score: float) -> ResolverConfidenceBand:
        thresholds = self.thresholds_for_shop(shop_id)
        if score >= thresholds.high:
            return ResolverConfidenceBand.HIGH
        if score >= thresholds.medium:
            return ResolverConfidenceBand.MEDIUM
        return ResolverConfidenceBand.LOW

    def update_thresholds(self, shop_id: UUID, thresholds: ResolverConfidenceThresholds) -> ResolverConfidenceThresholds:
        shop = self.shops.get_by_id(shop_id)
        if shop is None:
            return thresholds
        settings = dict(shop.agent_settings or {})
        catalog_settings = dict(settings.get(self.DEFAULT_KEY, {}))
        catalog_settings["confidence_thresholds"] = thresholds.model_dump()
        settings[self.DEFAULT_KEY] = catalog_settings
        shop.agent_settings = settings
        self.shops.commit()
        return thresholds
