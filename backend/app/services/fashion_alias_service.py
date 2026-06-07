from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models import ColorAlias, ProductSizeChart, SizeAlias, UnavailableDemandLog, User
from app.services.fashion_normalization import clean_fashion_text
from app.services.shop_service import ShopService


class FashionAliasService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.shop_service = ShopService(db)

    def list_color_aliases(self, shop_id: UUID, user: User) -> list[ColorAlias]:
        self.shop_service.get_shop(shop_id, user)
        return list(self.db.scalars(select(ColorAlias).where((ColorAlias.shop_id == shop_id) | (ColorAlias.shop_id.is_(None))).order_by(ColorAlias.shop_id.nullsfirst(), ColorAlias.raw_value)))

    def create_color_alias(self, shop_id: UUID, raw_value: str, normalized_value: str, language: str | None, user: User) -> ColorAlias:
        self.shop_service.get_shop(shop_id, user)
        alias = ColorAlias(shop_id=shop_id, raw_value=clean_fashion_text(raw_value) or raw_value.strip().casefold(), normalized_value=normalized_value.strip().casefold(), language=language or "und")
        self.db.add(alias); self.db.commit(); self.db.refresh(alias); return alias

    def update_color_alias(self, shop_id: UUID, alias_id: UUID, user: User, **changes) -> ColorAlias:
        alias = self._get_shop_color_alias(shop_id, alias_id, user)
        for field in ("raw_value", "normalized_value", "language", "is_active"):
            value = changes.get(field)
            if value is not None:
                if field == "raw_value":
                    value = clean_fashion_text(value) or value.strip().casefold()
                elif field == "normalized_value":
                    value = value.strip().casefold()
                setattr(alias, field, value)
        self.db.commit(); self.db.refresh(alias); return alias

    def delete_color_alias(self, shop_id: UUID, alias_id: UUID, user: User) -> None:
        alias = self._get_shop_color_alias(shop_id, alias_id, user)
        self.db.delete(alias); self.db.commit()

    def list_size_aliases(self, shop_id: UUID, user: User) -> list[SizeAlias]:
        self.shop_service.get_shop(shop_id, user)
        return list(self.db.scalars(select(SizeAlias).where((SizeAlias.shop_id == shop_id) | (SizeAlias.shop_id.is_(None))).order_by(SizeAlias.shop_id.nullsfirst(), SizeAlias.raw_value)))

    def create_size_alias(self, shop_id: UUID, raw_value: str, normalized_value: str, category: str | None, user: User) -> SizeAlias:
        self.shop_service.get_shop(shop_id, user)
        alias = SizeAlias(shop_id=shop_id, raw_value=clean_fashion_text(raw_value) or raw_value.strip().casefold(), normalized_value=normalized_value.strip().upper(), category=category)
        self.db.add(alias); self.db.commit(); self.db.refresh(alias); return alias

    def update_size_alias(self, shop_id: UUID, alias_id: UUID, user: User, **changes) -> SizeAlias:
        alias = self._get_shop_size_alias(shop_id, alias_id, user)
        for field in ("raw_value", "normalized_value", "category", "is_active"):
            value = changes.get(field)
            if value is not None:
                if field == "raw_value":
                    value = clean_fashion_text(value) or value.strip().casefold()
                elif field == "normalized_value":
                    value = value.strip().upper()
                setattr(alias, field, value)
        self.db.commit(); self.db.refresh(alias); return alias

    def delete_size_alias(self, shop_id: UUID, alias_id: UUID, user: User) -> None:
        alias = self._get_shop_size_alias(shop_id, alias_id, user)
        self.db.delete(alias); self.db.commit()

    def list_unavailable_demand(self, shop_id: UUID, user: User) -> list[UnavailableDemandLog]:
        self.shop_service.get_shop(shop_id, user)
        stmt = select(UnavailableDemandLog).where(UnavailableDemandLog.shop_id == shop_id).order_by(UnavailableDemandLog.created_at.desc())
        return list(self.db.scalars(stmt).all())

    def list_size_charts(self, shop_id: UUID, user: User) -> list[ProductSizeChart]:
        self.shop_service.get_shop(shop_id, user)
        return list(self.db.scalars(select(ProductSizeChart).where(ProductSizeChart.shop_id == shop_id).order_by(ProductSizeChart.category)))

    def create_size_chart(self, shop_id: UUID, product_id, category: str, chart_json: dict, user: User) -> ProductSizeChart:
        self.shop_service.get_shop(shop_id, user)
        chart = ProductSizeChart(shop_id=shop_id, product_id=product_id, category=category, chart_json=chart_json)
        self.db.add(chart); self.db.commit(); self.db.refresh(chart); return chart

    def _get_shop_color_alias(self, shop_id: UUID, alias_id: UUID, user: User) -> ColorAlias:
        self.shop_service.get_shop(shop_id, user)
        alias = self.db.scalar(select(ColorAlias).where(ColorAlias.id == alias_id, ColorAlias.shop_id == shop_id))
        if alias is None:
            raise HTTPException(status_code=404, detail="Color alias not found")
        return alias

    def _get_shop_size_alias(self, shop_id: UUID, alias_id: UUID, user: User) -> SizeAlias:
        self.shop_service.get_shop(shop_id, user)
        alias = self.db.scalar(select(SizeAlias).where(SizeAlias.id == alias_id, SizeAlias.shop_id == shop_id))
        if alias is None:
            raise HTTPException(status_code=404, detail="Size alias not found")
        return alias
