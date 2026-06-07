from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models import ColorAlias, ProductSizeChart, SizeAlias, User
from app.services.shop_service import ShopService


class FashionAliasService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.shop_service = ShopService(db)

    def list_color_aliases(self, shop_id: UUID, user: User) -> list[ColorAlias]:
        self.shop_service.get_shop(shop_id, user)
        return list(self.db.scalars(select(ColorAlias).where((ColorAlias.shop_id == shop_id) | (ColorAlias.shop_id.is_(None))).order_by(ColorAlias.raw_value)))

    def create_color_alias(self, shop_id: UUID, raw_value: str, normalized_value: str, language: str, user: User) -> ColorAlias:
        self.shop_service.get_shop(shop_id, user)
        alias = ColorAlias(shop_id=shop_id, raw_value=raw_value.strip().casefold(), normalized_value=normalized_value.strip().casefold(), language=language)
        self.db.add(alias); self.db.commit(); self.db.refresh(alias); return alias

    def list_size_aliases(self, shop_id: UUID, user: User) -> list[SizeAlias]:
        self.shop_service.get_shop(shop_id, user)
        return list(self.db.scalars(select(SizeAlias).where((SizeAlias.shop_id == shop_id) | (SizeAlias.shop_id.is_(None))).order_by(SizeAlias.raw_value)))

    def create_size_alias(self, shop_id: UUID, raw_value: str, normalized_value: str, category: str | None, user: User) -> SizeAlias:
        self.shop_service.get_shop(shop_id, user)
        alias = SizeAlias(shop_id=shop_id, raw_value=raw_value.strip().casefold(), normalized_value=normalized_value.strip().upper(), category=category)
        self.db.add(alias); self.db.commit(); self.db.refresh(alias); return alias

    def list_size_charts(self, shop_id: UUID, user: User) -> list[ProductSizeChart]:
        self.shop_service.get_shop(shop_id, user)
        return list(self.db.scalars(select(ProductSizeChart).where(ProductSizeChart.shop_id == shop_id).order_by(ProductSizeChart.category)))

    def create_size_chart(self, shop_id: UUID, product_id, category: str, chart_json: dict, user: User) -> ProductSizeChart:
        self.shop_service.get_shop(shop_id, user)
        chart = ProductSizeChart(shop_id=shop_id, product_id=product_id, category=category, chart_json=chart_json)
        self.db.add(chart); self.db.commit(); self.db.refresh(chart); return chart
