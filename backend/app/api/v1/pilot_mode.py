from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_shop_membership, require_shop_role
from app.db.session import get_db_session
from app.domain.enums import PilotModeScope, PilotOperatingMode, UserRole
from app.domain.models import ShopMember, User
from app.schemas.incident import IncidentRead
from app.schemas.pilot import EmergencyStopRequest, EmergencyStopResponse, EmergencyStopScopePreview, PilotModeUpdateRequest, PilotModeUpdateResponse
from app.schemas.pilot import PilotActionResponse, PilotEventRead, PilotSettingsRead
from app.services.incident_service import IncidentService
from app.services.pilot_mode_service import PilotModeService
from app.services.pilot_service import PilotService

router = APIRouter(prefix="/shops/{shop_id}/pilot-mode", tags=["pilot-mode"])


@router.patch("", response_model=PilotModeUpdateResponse)
def update_pilot_mode(
    shop_id: UUID,
    payload: PilotModeUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.ADMIN))],
    db: Annotated[Session, Depends(get_db_session)],
) -> PilotModeUpdateResponse:
    service = PilotModeService(db)
    settings, history = service.update_mode(
        shop_id,
        operating_mode=PilotOperatingMode(payload.operating_mode),
        scope=PilotModeScope(payload.scope),
        scope_ref=payload.scope_ref,
        reason=payload.reason,
        user_id=current_user.id,
        category_overrides=payload.category_overrides_json,
        campaign_overrides=payload.campaign_overrides_json,
    )
    return PilotModeUpdateResponse(
        pilot_settings=PilotSettingsRead.model_validate(settings),
        history_id=history.id,
    )


@router.post("/emergency-stop", response_model=EmergencyStopResponse)
def pilot_mode_emergency_stop(
    shop_id: UUID,
    payload: EmergencyStopRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.ADMIN))],
    db: Annotated[Session, Depends(get_db_session)],
) -> EmergencyStopResponse:
    service = PilotService(db)
    settings, event, scope_preview = service.set_emergency_stop(
        shop_id,
        True,
        user_id=current_user.id,
        reason=payload.reason,
    )
    incident_id = scope_preview.get("incident_id")
    return EmergencyStopResponse(
        pilot_settings=PilotSettingsRead.model_validate(settings),
        event=PilotService.to_event_read(event),
        scope_preview=EmergencyStopScopePreview(
            active_conversation_count=scope_preview["active_conversation_count"],
            simulation_conversation_count=scope_preview["simulation_conversation_count"],
            affected_conversation_ids=[UUID(value) for value in scope_preview.get("affected_conversation_ids", [])],
        ),
        incident_id=UUID(incident_id) if incident_id else None,
    )
