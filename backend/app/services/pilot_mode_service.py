from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.enums import PilotEventSeverity, PilotModeScope, PilotOperatingMode
from app.domain.models import PilotModeHistory, PilotSettings
from app.services.pilot_service import PilotService


class PilotModeService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.pilot_service = PilotService(db)

    def update_mode(
        self,
        shop_id: UUID,
        *,
        operating_mode: PilotOperatingMode,
        scope: PilotModeScope = PilotModeScope.GLOBAL,
        scope_ref: str | None = None,
        reason: str | None = None,
        user_id: UUID | None = None,
        category_overrides: dict | None = None,
        campaign_overrides: dict | None = None,
    ) -> tuple[PilotSettings, PilotModeHistory]:
        settings = self.pilot_service.get_or_create_settings(shop_id)
        previous_mode = settings.operating_mode
        settings.operating_mode = operating_mode
        if category_overrides is not None:
            settings.category_overrides_json = category_overrides
        if campaign_overrides is not None:
            settings.campaign_overrides_json = campaign_overrides
        history = PilotModeHistory(
            shop_id=shop_id,
            previous_mode=previous_mode,
            new_mode=operating_mode,
            scope=scope,
            scope_ref=scope_ref,
            changed_by_user_id=user_id,
            reason=reason,
        )
        self.db.add(history)
        self.pilot_service.log_event(
            shop_id,
            "operating_mode_changed",
            severity=PilotEventSeverity.INFO,
            title=f"Operating mode changed to {operating_mode.value}",
            description=reason,
            metadata={
                "previous_mode": previous_mode.value if previous_mode else None,
                "new_mode": operating_mode.value,
                "scope": scope.value,
                "scope_ref": scope_ref,
            },
            user_id=user_id,
            commit=False,
        )
        self.db.commit()
        self.db.refresh(settings)
        self.db.refresh(history)
        return settings, history

    def resolve_operating_mode(
        self,
        settings: PilotSettings,
        *,
        category: str | None = None,
        campaign: str | None = None,
    ) -> PilotOperatingMode:
        if category and category in (settings.category_overrides_json or {}):
            return PilotOperatingMode(settings.category_overrides_json[category])
        if campaign and campaign in (settings.campaign_overrides_json or {}):
            return PilotOperatingMode(settings.campaign_overrides_json[campaign])
        return settings.operating_mode
