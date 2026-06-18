from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.enums import (
    ConversationState,
    MessageChannel,
    MessageDirection,
    MessageType,
    TriggerSourceType,
)
from app.domain.models import (
    CommentToDmTrigger,
    Conversation,
    ConversationSlots,
    Customer,
    Message,
    TriggerEvent,
    User,
)
from app.schemas.triggers import (
    TriggerMatchRequest,
    TriggerMatchResponse,
    TriggerPerformanceRead,
    TriggerRuleCreate,
    TriggerRuleRead,
    TriggerRuleUpdate,
)
from app.services.legacy_channel_compat import get_instagram_channel_account_id
from app.services.shop_service import ShopService


class TriggerService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.shop_service = ShopService(db)

    def list_rules(self, shop_id: UUID, user: User) -> list[TriggerRuleRead]:
        self.shop_service.get_shop(shop_id, user)
        rules = self.db.scalars(
            select(CommentToDmTrigger)
            .where(CommentToDmTrigger.shop_id == shop_id)
            .order_by(CommentToDmTrigger.created_at.desc())
        ).all()
        return [TriggerRuleRead.model_validate(rule) for rule in rules]

    def create_rule(self, shop_id: UUID, payload: TriggerRuleCreate, user: User) -> TriggerRuleRead:
        self.shop_service.get_shop(shop_id, user)
        if self._duplicate_exists(shop_id, payload.instagram_account_id, payload.instagram_media_id, payload.source_type, payload.keyword):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Duplicate trigger rule for this account/media/source/keyword")
        rule = CommentToDmTrigger(shop_id=shop_id, **payload.model_dump())
        self.db.add(rule)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Duplicate trigger rule for this account/media/source/keyword") from exc
        self.db.refresh(rule)
        return TriggerRuleRead.model_validate(rule)

    def update_rule(self, shop_id: UUID, rule_id: UUID, payload: TriggerRuleUpdate, user: User) -> TriggerRuleRead:
        rule = self._get_rule(shop_id, rule_id, user)
        updates = payload.model_dump(exclude_unset=True)
        candidate_account = rule.instagram_account_id
        candidate_media = updates.get("instagram_media_id", rule.instagram_media_id)
        candidate_source = updates.get("source_type", rule.source_type)
        candidate_keyword = updates.get("keyword", rule.keyword)
        duplicate = self._find_exact_duplicate(shop_id, candidate_account, candidate_media, candidate_source, candidate_keyword)
        if duplicate and duplicate.id != rule.id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Duplicate trigger rule for this account/media/source/keyword")
        for field, value in updates.items():
            setattr(rule, field, value)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Duplicate trigger rule for this account/media/source/keyword") from exc
        self.db.refresh(rule)
        return TriggerRuleRead.model_validate(rule)

    def delete_rule(self, shop_id: UUID, rule_id: UUID, user: User) -> None:
        rule = self._get_rule(shop_id, rule_id, user)
        self.db.delete(rule)
        self.db.commit()

    def match_keyword(self, shop_id: UUID, payload: TriggerMatchRequest, user: User) -> TriggerMatchResponse:
        self.shop_service.get_shop(shop_id, user)
        rule = self._find_match(shop_id, payload.instagram_account_id, payload.text, payload.source_type, payload.instagram_media_id)
        if not rule:
            return TriggerMatchResponse(matched=False)
        customer = self.db.scalar(select(Customer).where(Customer.shop_id == shop_id, Customer.instagram_user_id == payload.instagram_user_id))
        if customer is None:
            customer = Customer(shop_id=shop_id, instagram_user_id=payload.instagram_user_id)
            self.db.add(customer)
            self.db.flush()
        channel_account_id = get_instagram_channel_account_id(
            self.db, payload.instagram_account_id
        )
        conversation = Conversation(
            shop_id=shop_id,
            instagram_account_id=payload.instagram_account_id,
            channel_account_id=channel_account_id,
            external_conversation_id=payload.instagram_user_id,
            customer_id=customer.id,
            state=ConversationState.OPEN,
            channel_provider=MessageChannel.INSTAGRAM.value,
            channel_conversation_id=payload.instagram_user_id,
            channel_customer_id=payload.instagram_user_id,
            trigger_rule_id=rule.id,
        )
        self.db.add(conversation)
        self.db.flush()
        slots = ConversationSlots(conversation_id=conversation.id, product_id=rule.target_product_id)
        self.db.add(slots)
        message_metadata = {
            "shop_id": shop_id,
            "customer_id": customer.id,
            "channel_provider": MessageChannel.INSTAGRAM.value,
            "channel_account_id": channel_account_id,
        }
        self.db.add(Message(**message_metadata, conversation_id=conversation.id, direction=MessageDirection.INBOUND, channel=MessageChannel.INSTAGRAM, message_type=MessageType.TEXT, text=payload.text, raw_payload={"trigger_source_type": payload.source_type.value}))
        self.db.add(Message(**message_metadata, conversation_id=conversation.id, direction=MessageDirection.OUTBOUND, channel=MessageChannel.INSTAGRAM, message_type=MessageType.TEXT, text=rule.response_template, raw_payload={"simulation": True, "trigger_rule_id": str(rule.id)}))
        self.db.add(TriggerEvent(trigger_id=rule.id, conversation_id=conversation.id, customer_id=customer.id, matched_keyword=rule.keyword, source_type=rule.source_type, dm_sent=True))
        self.db.commit()
        return TriggerMatchResponse(matched=True, trigger_id=rule.id, response_text=rule.response_template, target_product_id=rule.target_product_id, conversation_id=conversation.id)

    def performance(self, shop_id: UUID, user: User) -> list[TriggerPerformanceRead]:
        self.shop_service.get_shop(shop_id, user)
        rules = self.list_rules(shop_id, user)
        rows: list[TriggerPerformanceRead] = []
        for rule in rules:
            events = list(self.db.scalars(select(TriggerEvent).where(TriggerEvent.trigger_id == rule.id)))
            paid = [event for event in events if event.paid_order_id is not None]
            revenue = sum((Decimal(str(event.revenue_amount)) for event in paid), Decimal("0"))
            rows.append(TriggerPerformanceRead(trigger_id=rule.id, keyword=rule.keyword, source_type=rule.source_type, impressions=len(events), dm_sent=sum(1 for event in events if event.dm_sent), paid_orders=len(paid), revenue=revenue, conversion_rate=round(len(paid) / len(events), 4) if events else 0.0))
        return rows


    def _duplicate_exists(self, shop_id: UUID, account_id: UUID, media_id: str | None, source_type: TriggerSourceType, keyword: str) -> bool:
        return self._find_exact_duplicate(shop_id, account_id, media_id, source_type, keyword) is not None

    def _find_exact_duplicate(self, shop_id: UUID, account_id: UUID, media_id: str | None, source_type: TriggerSourceType, keyword: str) -> CommentToDmTrigger | None:
        candidates = self.db.scalars(select(CommentToDmTrigger).where(CommentToDmTrigger.shop_id == shop_id, CommentToDmTrigger.instagram_account_id == account_id, CommentToDmTrigger.source_type == source_type, CommentToDmTrigger.keyword == keyword.strip())).all()
        return next((rule for rule in candidates if rule.instagram_media_id == media_id), None)

    def _find_match(self, shop_id: UUID, account_id: UUID, text: str, source_type: TriggerSourceType, media_id: str | None) -> CommentToDmTrigger | None:
        normalized = text.casefold().strip()
        candidates = self.db.scalars(select(CommentToDmTrigger).where(CommentToDmTrigger.shop_id == shop_id, CommentToDmTrigger.instagram_account_id == account_id, CommentToDmTrigger.source_type == source_type, CommentToDmTrigger.is_active.is_(True))).all()
        scoped = [r for r in candidates if r.instagram_media_id in (media_id, None)]
        return next((rule for rule in scoped if rule.keyword.casefold().strip() in normalized), None)

    def _get_rule(self, shop_id: UUID, rule_id: UUID, user: User) -> CommentToDmTrigger:
        self.shop_service.get_shop(shop_id, user)
        rule = self.db.get(CommentToDmTrigger, rule_id)
        if not rule or rule.shop_id != shop_id:
            raise HTTPException(status_code=404, detail="Trigger rule not found")
        return rule
