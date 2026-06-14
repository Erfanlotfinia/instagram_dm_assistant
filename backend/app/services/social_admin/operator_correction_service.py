from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models import AutomationRuleSuggestion, Conversation, OperatorCorrection, User
from app.schemas.social_admin import (
    AutomationSuggestionRead,
    OperatorCorrectionCreate,
    OperatorCorrectionRead,
)
from app.services.shop_service import ShopService

CORRECTION_FIELDS = (
    "scenario",
    "product",
    "attribute",
    "reference",
    "response",
    "decision_channel",
)


class OperatorCorrectionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.shop_service = ShopService(db)

    def list_corrections(self, shop_id: UUID, user: User, limit: int = 50) -> list[OperatorCorrectionRead]:
        self.shop_service.get_shop(shop_id, user)
        rows = list(
            self.db.scalars(
                select(OperatorCorrection)
                .where(OperatorCorrection.shop_id == shop_id)
                .order_by(OperatorCorrection.created_at.desc())
                .limit(limit)
            ).all()
        )
        return [OperatorCorrectionRead.model_validate(row) for row in rows]

    def create_correction(
        self, shop_id: UUID, payload: OperatorCorrectionCreate, user: User
    ) -> list[OperatorCorrectionRead]:
        self.shop_service.get_shop(shop_id, user)
        conversation = self.db.scalar(
            select(Conversation).where(
                Conversation.id == payload.conversation_id,
                Conversation.shop_id == shop_id,
            )
        )
        if conversation is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

        created: list[OperatorCorrection] = []
        for field in CORRECTION_FIELDS:
            before_value = payload.before_json.get(field)
            after_value = payload.after_json.get(field)
            if after_value in (None, "") or before_value == after_value:
                continue

            correction = OperatorCorrection(
                shop_id=shop_id,
                conversation_id=payload.conversation_id,
                message_id=payload.message_id,
                correction_type=field,
                before_json={field: before_value} if before_value is not None else {},
                after_json={field: after_value},
                operator_id=user.id,
            )
            self.db.add(correction)
            self.db.flush()
            created.append(correction)

            suggestion = AutomationRuleSuggestion(
                shop_id=shop_id,
                source_correction_id=correction.id,
                suggested_rule_json=self._build_suggestion(field, before_value, after_value, payload),
                status="pending",
            )
            self.db.add(suggestion)

        if not created:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Provide at least one corrected field that differs from the before state",
            )

        self.db.commit()
        for correction in created:
            self.db.refresh(correction)
        return [OperatorCorrectionRead.model_validate(correction) for correction in created]

    def _build_suggestion(
        self,
        field: str,
        before_value: Any,
        after_value: Any,
        payload: OperatorCorrectionCreate,
    ) -> dict[str, Any]:
        if field == "scenario":
            return {
                "type": "rule",
                "title": "Scenario routing rule",
                "summary": f"Route similar messages to {after_value} instead of {before_value or 'unknown'}.",
                "rule": {
                    "scenario": after_value,
                    "previous_scenario": before_value,
                    "conversation_id": str(payload.conversation_id),
                },
            }
        if field in {"product", "attribute"}:
            return {
                "type": "alias",
                "title": f"{field.title()} alias",
                "summary": f'Map "{before_value or "customer phrasing"}" to "{after_value}".',
                "alias": {
                    "field": field,
                    "from": before_value,
                    "to": after_value,
                },
            }
        if field == "reference":
            return {
                "type": "rule",
                "title": "Reference resolution rule",
                "summary": f'Resolve references like "{before_value or "ambiguous"}" to {after_value}.',
                "rule": {
                    "reference_from": before_value,
                    "reference_to": after_value,
                },
            }
        if field == "response":
            return {
                "type": "regression_test",
                "title": "Regression test from corrected response",
                "summary": "Lock this corrected reply into the scenario regression pack.",
                "test": {
                    "expected_response": after_value,
                    "previous_response": before_value,
                    "conversation_id": str(payload.conversation_id),
                },
            }
        return {
            "type": "rule",
            "title": "Handler routing rule",
            "summary": f"Prefer {after_value} over {before_value or 'automation'} for similar cases.",
            "rule": {
                "decision_channel": after_value,
                "previous_channel": before_value,
            },
        }


class AutomationSuggestionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.shop_service = ShopService(db)

    def list_suggestions(
        self, shop_id: UUID, user: User, status_filter: str | None = None, limit: int = 50
    ) -> list[AutomationSuggestionRead]:
        self.shop_service.get_shop(shop_id, user)
        stmt = select(AutomationRuleSuggestion).where(AutomationRuleSuggestion.shop_id == shop_id)
        if status_filter:
            stmt = stmt.where(AutomationRuleSuggestion.status == status_filter)
        rows = list(
            self.db.scalars(stmt.order_by(AutomationRuleSuggestion.created_at.desc()).limit(limit)).all()
        )
        return [AutomationSuggestionRead.model_validate(row) for row in rows]

    def approve_suggestion(self, shop_id: UUID, suggestion_id: UUID, user: User) -> AutomationSuggestionRead:
        suggestion = self._get_suggestion(shop_id, suggestion_id, user)
        suggestion.status = "approved"
        self.db.commit()
        self.db.refresh(suggestion)
        return AutomationSuggestionRead.model_validate(suggestion)

    def reject_suggestion(self, shop_id: UUID, suggestion_id: UUID, user: User) -> AutomationSuggestionRead:
        suggestion = self._get_suggestion(shop_id, suggestion_id, user)
        suggestion.status = "rejected"
        self.db.commit()
        self.db.refresh(suggestion)
        return AutomationSuggestionRead.model_validate(suggestion)

    def _get_suggestion(self, shop_id: UUID, suggestion_id: UUID, user: User) -> AutomationRuleSuggestion:
        self.shop_service.get_shop(shop_id, user)
        suggestion = self.db.scalar(
            select(AutomationRuleSuggestion).where(
                AutomationRuleSuggestion.shop_id == shop_id,
                AutomationRuleSuggestion.id == suggestion_id,
            )
        )
        if suggestion is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suggestion not found")
        return suggestion
