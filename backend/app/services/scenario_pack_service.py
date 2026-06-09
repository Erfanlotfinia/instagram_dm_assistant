from __future__ import annotations

import itertools
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import MessageDirection, ScenarioPackType
from app.domain.models import Conversation, Message, ScenarioPack, User
from app.schemas.scenario import ScenarioPackCreateRequest, ScenarioPackRead


class ScenarioPackService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, shop_id: UUID, payload: ScenarioPackCreateRequest, user: User | None = None) -> ScenarioPack:
        if payload.pack_type == ScenarioPackType.SYNTHETIC:
            scenarios = self._generate_synthetic(payload.template or {}, payload.count or 3)
        elif payload.pack_type == ScenarioPackType.INCIDENT_REPLAY:
            if not payload.conversation_ids:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="conversation_ids required")
            scenarios = self._build_incident_replay(payload.conversation_ids)
        else:
            scenarios = payload.scenarios_json

        pack = ScenarioPack(
            shop_id=shop_id,
            name=payload.name,
            pack_type=payload.pack_type,
            description=payload.description,
            scenarios_json=scenarios,
            is_golden=payload.is_golden,
            created_by_user_id=user.id if user else None,
        )
        self.db.add(pack)
        self.db.commit()
        self.db.refresh(pack)
        return pack

    def list_for_shop(self, shop_id: UUID) -> list[ScenarioPack]:
        return list(
            self.db.scalars(
                select(ScenarioPack).where(ScenarioPack.shop_id == shop_id).order_by(ScenarioPack.created_at.desc())
            ).all()
        )

    def get(self, shop_id: UUID, pack_id: UUID) -> ScenarioPack | None:
        return self.db.scalar(
            select(ScenarioPack).where(ScenarioPack.id == pack_id, ScenarioPack.shop_id == shop_id)
        )

    @staticmethod
    def to_read(pack: ScenarioPack) -> ScenarioPackRead:
        return ScenarioPackRead.model_validate(pack)

    def _generate_synthetic(self, template: dict, count: int) -> list[dict]:
        colors = template.get("colors") or ["black", "cream"]
        sizes = template.get("sizes") or ["M", "L"]
        messages = template.get("messages") or ["می‌خوام {color} سایز {size}"]
        scenarios: list[dict] = []
        for idx, (color, size) in enumerate(itertools.islice(itertools.product(colors, sizes), count)):
            message_template = messages[idx % len(messages)]
            scenarios.append(
                {
                    "item_key": f"synthetic-{idx + 1}",
                    "message_text": message_template.format(color=color, size=size),
                    "expected_json": template.get("expected_json") or {},
                }
            )
        return scenarios

    def _build_incident_replay(self, conversation_ids: list[UUID]) -> list[dict]:
        scenarios: list[dict] = []
        for conversation_id in conversation_ids:
            conversation = self.db.get(Conversation, conversation_id)
            if conversation is None:
                continue
            inbound = self.db.scalar(
                select(Message)
                .where(Message.conversation_id == conversation_id, Message.direction == MessageDirection.INBOUND)
                .order_by(Message.created_at.asc())
                .limit(1)
            )
            if inbound is None:
                continue
            scenarios.append(
                {
                    "item_key": f"incident-{conversation_id}",
                    "message_text": inbound.text or "",
                    "expected_json": {
                        "intent": conversation.last_intent,
                        "requires_handoff": conversation.handoff_required,
                    },
                    "source_conversation_id": str(conversation_id),
                }
            )
        return scenarios
