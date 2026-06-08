from __future__ import annotations

import logging
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.enums import ProductStatus, UpsellSuggestionStatus
from app.domain.models import Product, ProductUpsell, UpsellSuggestion, User
from app.services.shop_service import ShopService

logger = logging.getLogger(__name__)


class UpsellService:
    DEFAULT_TEMPLATE = "You might also like {target_product_title} — {target_price} {currency}."

    def __init__(self, db: Session) -> None:
        self.db = db
        self.shop_service = ShopService(db)

    def list_rules(self, shop_id: UUID, user: User) -> list[ProductUpsell]:
        self.shop_service.get_shop(shop_id, user)
        return list(
            self.db.scalars(
                select(ProductUpsell)
                .where(ProductUpsell.shop_id == shop_id)
                .order_by(ProductUpsell.created_at.desc())
            ).all()
        )

    def create_rule(self, shop_id: UUID, payload, user: User) -> ProductUpsell:
        self.shop_service.get_shop(shop_id, user)
        if payload.source_product_id == payload.target_product_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Source and target products must differ",
            )
        self._ensure_product(shop_id, payload.source_product_id)
        self._ensure_product(shop_id, payload.target_product_id)
        rule = ProductUpsell(shop_id=shop_id, **payload.model_dump())
        self.db.add(rule)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Upsell rule already exists") from exc
        self.db.refresh(rule)
        return rule

    def update_rule(self, shop_id: UUID, rule_id: UUID, payload, user: User) -> ProductUpsell:
        rule = self._get_rule(shop_id, rule_id, user)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(rule, field, value)
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def delete_rule(self, shop_id: UUID, rule_id: UUID, user: User) -> None:
        rule = self._get_rule(shop_id, rule_id, user)
        self.db.delete(rule)
        self.db.commit()

    def maybe_suggest_upsell(
        self,
        *,
        shop_id: UUID,
        conversation_id: UUID,
        order,
        source_product_id: UUID,
        intent_confidence: float,
        handoff_required: bool,
        workflow_clear: bool,
    ) -> UpsellSuggestion | None:
        if handoff_required or not workflow_clear:
            return self._log_skipped(
                shop_id, conversation_id, order, source_product_id, "handoff_or_unclear_order"
            )
        if intent_confidence < 0.75:
            return self._log_skipped(
                shop_id, conversation_id, order, source_product_id, "low_confidence"
            )

        rule = self.db.scalar(
            select(ProductUpsell)
            .where(
                ProductUpsell.shop_id == shop_id,
                ProductUpsell.source_product_id == source_product_id,
                ProductUpsell.is_active.is_(True),
            )
            .order_by(ProductUpsell.created_at.desc())
            .limit(1)
        )
        if rule is None:
            return None

        existing = self.db.scalar(
            select(UpsellSuggestion).where(
                UpsellSuggestion.conversation_id == conversation_id,
                UpsellSuggestion.source_product_id == source_product_id,
                UpsellSuggestion.status == UpsellSuggestionStatus.SUGGESTED,
            )
        )
        if existing is not None:
            return existing

        target = self.db.get(Product, rule.target_product_id)
        if target is None or target.status != ProductStatus.ACTIVE:
            return self._log_skipped(
                shop_id, conversation_id, order, source_product_id, "target_unavailable"
            )

        template = rule.message_template or self.DEFAULT_TEMPLATE
        suggested_text = (
            template.replace("{target_product_title}", target.title)
            .replace("{target_price}", str(target.base_price or "0"))
            .replace("{currency}", target.currency)
        )
        suggestion = UpsellSuggestion(
            shop_id=shop_id,
            conversation_id=conversation_id,
            order_id=order.id if order else None,
            source_product_id=source_product_id,
            target_product_id=rule.target_product_id,
            suggested_text=suggested_text,
            status=UpsellSuggestionStatus.SUGGESTED,
        )
        self.db.add(suggestion)
        self.db.flush()
        logger.info(
            "Logged upsell suggestion conversation=%s target=%s",
            conversation_id,
            rule.target_product_id,
        )
        return suggestion

    def _log_skipped(
        self,
        shop_id: UUID,
        conversation_id: UUID,
        order,
        source_product_id: UUID,
        reason: str,
    ) -> UpsellSuggestion | None:
        rule = self.db.scalar(
            select(ProductUpsell)
            .where(
                ProductUpsell.shop_id == shop_id,
                ProductUpsell.source_product_id == source_product_id,
                ProductUpsell.is_active.is_(True),
            )
            .limit(1)
        )
        if rule is None:
            return None
        suggestion = UpsellSuggestion(
            shop_id=shop_id,
            conversation_id=conversation_id,
            order_id=order.id if order else None,
            source_product_id=source_product_id,
            target_product_id=rule.target_product_id,
            suggested_text=f"[skipped: {reason}]",
            status=UpsellSuggestionStatus.SKIPPED,
        )
        self.db.add(suggestion)
        self.db.flush()
        return suggestion

    def _get_rule(self, shop_id: UUID, rule_id: UUID, user: User) -> ProductUpsell:
        self.shop_service.get_shop(shop_id, user)
        rule = self.db.scalar(
            select(ProductUpsell).where(ProductUpsell.id == rule_id, ProductUpsell.shop_id == shop_id)
        )
        if rule is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upsell rule not found")
        return rule

    def _ensure_product(self, shop_id: UUID, product_id: UUID) -> Product:
        product = self.db.scalar(
            select(Product).where(Product.id == product_id, Product.shop_id == shop_id)
        )
        if product is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
        return product

    @staticmethod
    def count_suggestions(db: Session, shop_id: UUID) -> tuple[int, int]:
        total = db.scalar(
            select(func.count(UpsellSuggestion.id)).where(
                UpsellSuggestion.shop_id == shop_id,
                UpsellSuggestion.status == UpsellSuggestionStatus.SUGGESTED,
            )
        ) or 0
        accepted = db.scalar(
            select(func.count(UpsellSuggestion.id)).where(
                UpsellSuggestion.shop_id == shop_id,
                UpsellSuggestion.status == UpsellSuggestionStatus.ACCEPTED,
            )
        ) or 0
        return int(total), int(accepted)
