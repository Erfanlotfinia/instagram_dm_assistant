from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.domain.enums import CatalogAliasSource, ResolverFeedbackAction
from app.domain.models import ProductAlias, ResolverFeedback, User
from app.repositories.catalog_repository import ProductAliasRepository
from app.repositories.resolver_repository import ResolverFeedbackRepository, ResolverTraceRepository
from app.schemas.resolve import ResolverFeedbackRead, ResolverFeedbackRequest
from app.services.shop_service import ShopService


class ResolverFeedbackService:
    """Operator feedback loop for resolver corrections."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.shop_service = ShopService(db)
        self.traces = ResolverTraceRepository(db)
        self.feedback = ResolverFeedbackRepository(db)
        self.aliases = ProductAliasRepository(db)

    def submit_feedback(
        self,
        shop_id: UUID,
        trace_id: UUID,
        payload: ResolverFeedbackRequest,
        user: User,
    ) -> ResolverFeedbackRead:
        self.shop_service.get_shop(shop_id, user)
        trace = self.traces.get_for_shop(shop_id, trace_id)
        if trace is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trace not found")

        try:
            action = ResolverFeedbackAction(payload.action)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid feedback action") from exc

        entry = ResolverFeedback(
            shop_id=shop_id,
            trace_id=trace_id,
            action=action,
            operator_id=user.id,
            original_product_id=payload.original_product_id,
            corrected_product_id=payload.corrected_product_id,
            original_variant_id=payload.original_variant_id,
            corrected_variant_id=payload.corrected_variant_id,
            notes=payload.notes,
        )
        self.feedback.add(entry)
        self._apply_feedback_aliases(shop_id, action, payload)
        self.feedback.commit()
        return ResolverFeedbackRead.model_validate(entry)

    def list_for_trace(self, shop_id: UUID, trace_id: UUID, user: User) -> list[ResolverFeedbackRead]:
        self.shop_service.get_shop(shop_id, user)
        return [ResolverFeedbackRead.model_validate(item) for item in self.feedback.list_for_trace(shop_id, trace_id)]

    def _apply_feedback_aliases(self, shop_id: UUID, action: ResolverFeedbackAction, payload: ResolverFeedbackRequest) -> None:
        if action == ResolverFeedbackAction.CORRECT_PRODUCT and payload.corrected_product_id and payload.notes:
            alias_text = payload.notes.strip().casefold()
            if not alias_text:
                return
            conflict = self.aliases.find_by_alias(shop_id, alias_text)
            if conflict:
                return
            self.aliases.add(
                ProductAlias(
                    shop_id=shop_id,
                    product_id=payload.corrected_product_id,
                    alias_text=alias_text,
                    language="und",
                    source=CatalogAliasSource.OPERATOR_FEEDBACK,
                    confidence=1.0,
                )
            )
