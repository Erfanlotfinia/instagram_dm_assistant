from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_shop_membership, require_shop_role
from app.db.session import get_db_session
from app.domain.enums import UserRole
from app.domain.models import ShopMember, User
from app.schemas.social_admin import (
    AdminTaskCreate,
    AdminTaskRead,
    AutomationRuleStepRead,
    AutomationSuggestionRead,
    OperatorCorrectionCreate,
    OperatorCorrectionRead,
)
from app.services.social_admin.admin_task_service import AdminTaskService
from app.services.social_admin.automation_rules_service import AutomationRulesService
from app.services.social_admin.operator_correction_service import (
    AutomationSuggestionService,
    OperatorCorrectionService,
)

router = APIRouter(prefix="/shops/{shop_id}", tags=["social-admin"])


@router.get("/automation-rules", response_model=list[AutomationRuleStepRead])
def list_automation_rules(
    shop_id: UUID,
    _user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
) -> list[AutomationRuleStepRead]:
    return AutomationRulesService().list_priority_steps()


@router.get("/admin-tasks", response_model=list[AdminTaskRead])
def list_admin_tasks(
    shop_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
    db: Annotated[Session, Depends(get_db_session)],
) -> list[AdminTaskRead]:
    return AdminTaskService(db).list_tasks(shop_id, current_user)


@router.post("/admin-tasks", response_model=AdminTaskRead, status_code=201)
def create_admin_task(
    shop_id: UUID,
    payload: AdminTaskCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.OPERATOR))],
    db: Annotated[Session, Depends(get_db_session)],
) -> AdminTaskRead:
    return AdminTaskService(db).create_task(shop_id, payload, current_user)


@router.post("/admin-tasks/{task_id}/approve", response_model=AdminTaskRead)
def approve_admin_task(
    shop_id: UUID,
    task_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.OPERATOR))],
    db: Annotated[Session, Depends(get_db_session)],
) -> AdminTaskRead:
    return AdminTaskService(db).approve_task(shop_id, task_id, current_user)


@router.post("/admin-tasks/{task_id}/reject", response_model=AdminTaskRead)
def reject_admin_task(
    shop_id: UUID,
    task_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.OPERATOR))],
    db: Annotated[Session, Depends(get_db_session)],
) -> AdminTaskRead:
    return AdminTaskService(db).reject_task(shop_id, task_id, current_user)


@router.get("/operator-corrections", response_model=list[OperatorCorrectionRead])
def list_operator_corrections(
    shop_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
    db: Annotated[Session, Depends(get_db_session)],
) -> list[OperatorCorrectionRead]:
    return OperatorCorrectionService(db).list_corrections(shop_id, current_user)


@router.post("/operator-corrections", response_model=list[OperatorCorrectionRead], status_code=201)
def create_operator_correction(
    shop_id: UUID,
    payload: OperatorCorrectionCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.OPERATOR))],
    db: Annotated[Session, Depends(get_db_session)],
) -> list[OperatorCorrectionRead]:
    return OperatorCorrectionService(db).create_correction(shop_id, payload, current_user)


@router.get("/automation-suggestions", response_model=list[AutomationSuggestionRead])
def list_automation_suggestions(
    shop_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
    db: Annotated[Session, Depends(get_db_session)],
    status: str | None = None,
) -> list[AutomationSuggestionRead]:
    return AutomationSuggestionService(db).list_suggestions(shop_id, current_user, status_filter=status)


@router.post("/automation-suggestions/{suggestion_id}/approve", response_model=AutomationSuggestionRead)
def approve_automation_suggestion(
    shop_id: UUID,
    suggestion_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.ADMIN))],
    db: Annotated[Session, Depends(get_db_session)],
) -> AutomationSuggestionRead:
    return AutomationSuggestionService(db).approve_suggestion(shop_id, suggestion_id, current_user)


@router.post("/automation-suggestions/{suggestion_id}/reject", response_model=AutomationSuggestionRead)
def reject_automation_suggestion(
    shop_id: UUID,
    suggestion_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.ADMIN))],
    db: Annotated[Session, Depends(get_db_session)],
) -> AutomationSuggestionRead:
    return AutomationSuggestionService(db).reject_suggestion(shop_id, suggestion_id, current_user)
