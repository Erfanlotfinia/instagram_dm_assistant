from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models import ResolverFeedback, ResolverTrace, VariantAlias


class ResolverTraceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_for_shop(self, shop_id: UUID, trace_id: UUID) -> ResolverTrace | None:
        stmt = select(ResolverTrace).where(
            ResolverTrace.id == trace_id,
            ResolverTrace.shop_id == shop_id,
        )
        return self.db.scalar(stmt)

    def add(self, trace: ResolverTrace) -> ResolverTrace:
        self.db.add(trace)
        self.db.flush()
        return trace

    def commit(self) -> None:
        self.db.commit()

    def refresh(self, trace: ResolverTrace) -> None:
        self.db.refresh(trace)


class ResolverFeedbackRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_trace(self, shop_id: UUID, trace_id: UUID) -> list[ResolverFeedback]:
        stmt = select(ResolverFeedback).where(
            ResolverFeedback.shop_id == shop_id,
            ResolverFeedback.trace_id == trace_id,
        )
        return list(self.db.scalars(stmt.order_by(ResolverFeedback.created_at.desc())))

    def add(self, feedback: ResolverFeedback) -> ResolverFeedback:
        self.db.add(feedback)
        self.db.flush()
        return feedback

    def commit(self) -> None:
        self.db.commit()


class VariantAliasRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_variant(self, shop_id: UUID, variant_id: UUID) -> list[VariantAlias]:
        stmt = select(VariantAlias).where(
            VariantAlias.shop_id == shop_id,
            VariantAlias.variant_id == variant_id,
            VariantAlias.is_active.is_(True),
        )
        return list(self.db.scalars(stmt))

    def find_matching(self, shop_id: UUID, text: str) -> list[VariantAlias]:
        pattern = f"%{text}%"
        stmt = select(VariantAlias).where(
            VariantAlias.shop_id == shop_id,
            VariantAlias.is_active.is_(True),
            VariantAlias.alias_text.ilike(pattern),
        )
        return list(self.db.scalars(stmt))

    def add(self, entity: VariantAlias) -> VariantAlias:
        self.db.add(entity)
        self.db.flush()
        return entity

    def commit(self) -> None:
        self.db.commit()
