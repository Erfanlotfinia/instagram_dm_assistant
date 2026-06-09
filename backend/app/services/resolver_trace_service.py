from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.enums import ResolverConfidenceBand, ResolverTraceType
from app.domain.models import ResolverTrace
from app.repositories.resolver_repository import ResolverTraceRepository
from app.schemas.resolve import ResolveProductRequest, ResolveVariantRequest, ResolverTraceRead


class ResolverTraceService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.traces = ResolverTraceRepository(db)

    def get_trace(self, shop_id: UUID, trace_id: UUID) -> ResolverTraceRead | None:
        trace = self.traces.get_for_shop(shop_id, trace_id)
        if trace is None:
            return None
        return ResolverTraceRead.model_validate(trace)

    def create_product_trace(
        self,
        *,
        shop_id: UUID,
        payload: ResolveProductRequest,
        candidates: list[dict],
        matched_aliases: list[dict],
        rules_fired: list[str],
        missing_slots: list[str],
        confidence_score: float,
        confidence_band: ResolverConfidenceBand,
        rationale: str | None,
        qdrant_metadata: dict,
        conversation_id: UUID | None,
    ) -> ResolverTrace:
        trace = ResolverTrace(
            shop_id=shop_id,
            trace_type=ResolverTraceType.PRODUCT,
            conversation_id=conversation_id,
            input_payload=payload.model_dump(mode="json"),
            top_candidates=candidates,
            matched_aliases=matched_aliases,
            rules_fired=rules_fired,
            missing_slots=missing_slots,
            confidence_band=confidence_band,
            confidence_score=confidence_score,
            rationale=rationale,
            qdrant_query_metadata=qdrant_metadata,
        )
        self.traces.add(trace)
        self.traces.commit()
        self.traces.refresh(trace)
        return trace

    def create_variant_trace(
        self,
        *,
        shop_id: UUID,
        payload: ResolveVariantRequest,
        candidates: list[dict],
        matched_aliases: list[dict],
        rules_fired: list[str],
        missing_slots: list[str],
        confidence_score: float,
        confidence_band: ResolverConfidenceBand,
        rationale: str | None,
        qdrant_metadata: dict,
        conversation_id: UUID | None,
    ) -> ResolverTrace:
        trace = ResolverTrace(
            shop_id=shop_id,
            trace_type=ResolverTraceType.VARIANT,
            conversation_id=conversation_id,
            input_payload=payload.model_dump(mode="json"),
            top_candidates=candidates,
            matched_aliases=matched_aliases,
            rules_fired=rules_fired,
            missing_slots=missing_slots,
            confidence_band=confidence_band,
            confidence_score=confidence_score,
            rationale=rationale,
            qdrant_query_metadata=qdrant_metadata,
        )
        self.traces.add(trace)
        self.traces.commit()
        self.traces.refresh(trace)
        return trace
