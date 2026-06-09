from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import OrderCorrectnessAction
from app.domain.models import PilotMode


class PilotModeRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_for_action(self, shop_id: UUID, action: OrderCorrectnessAction) -> PilotMode | None:
        stmt = select(PilotMode).where(
            PilotMode.shop_id == shop_id,
            PilotMode.action == action,
        )
        return self.db.scalar(stmt)

    def list_for_shop(self, shop_id: UUID) -> list[PilotMode]:
        stmt = select(PilotMode).where(PilotMode.shop_id == shop_id)
        return list(self.db.scalars(stmt).all())

    def ensure_defaults(self, shop_id: UUID) -> None:
        for action in OrderCorrectnessAction:
            existing = self.get_for_action(shop_id, action)
            if existing is None:
                self.db.add(
                    PilotMode(
                        shop_id=shop_id,
                        action=action,
                        permitted=True,
                        confidence_threshold=0.6,
                        require_customer_confirmation=False,
                    )
                )
        self.db.flush()
