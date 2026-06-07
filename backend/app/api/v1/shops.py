from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_shop_role
from app.db.session import get_db_session
from app.domain.enums import UserRole
from app.domain.models import ShopMember, User
from app.schemas.dashboard import DashboardMetrics
from app.schemas.instagram_account import InstagramAccountCreate, InstagramAccountRead
from app.schemas.shop import ShopAgentSettings, ShopCreate, ShopMemberRead, ShopRead, ShopSettingsRead, ShopUpdate
from app.services.dashboard_service import DashboardService
from app.services.instagram_account_service import InstagramAccountService
from app.services.shop_service import ShopService

router = APIRouter(prefix="/shops", tags=["shops"])


@router.get("", response_model=list[ShopRead])
def list_shops(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
) -> list[ShopRead]:
    return ShopService(db).list_shops_for_user(current_user)


@router.post("", response_model=ShopRead, status_code=201)
def create_shop(
    payload: ShopCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
) -> ShopRead:
    return ShopService(db).create_shop(payload, current_user)


@router.get("/{shop_id}", response_model=ShopRead)
def get_shop(
    shop_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
) -> ShopRead:
    return ShopService(db).get_shop(shop_id, current_user)


@router.patch("/{shop_id}", response_model=ShopRead)
def update_shop(
    shop_id: UUID,
    payload: ShopUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.ADMIN))],
    db: Annotated[Session, Depends(get_db_session)],
) -> ShopRead:
    return ShopService(db).update_shop(shop_id, payload, current_user)


@router.get("/{shop_id}/settings", response_model=ShopSettingsRead)
def get_shop_settings(
    shop_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
) -> ShopSettingsRead:
    return ShopService(db).get_settings(shop_id, current_user)


@router.patch("/{shop_id}/agent-settings", response_model=ShopRead)
def update_agent_settings(
    shop_id: UUID,
    payload: ShopAgentSettings,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.ADMIN))],
    db: Annotated[Session, Depends(get_db_session)],
) -> ShopRead:
    return ShopService(db).update_agent_settings(shop_id, payload, current_user)


@router.get("/{shop_id}/dashboard/metrics", response_model=DashboardMetrics)
def get_dashboard_metrics(
    shop_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
) -> DashboardMetrics:
    return DashboardService(db).get_metrics(shop_id, current_user)


@router.get("/{shop_id}/members", response_model=list[ShopMemberRead])
def list_shop_members(
    shop_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
) -> list[ShopMemberRead]:
    return ShopService(db).list_members(shop_id, current_user)


@router.get("/{shop_id}/instagram-accounts", response_model=list[InstagramAccountRead])
def list_instagram_accounts(
    shop_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
) -> list[InstagramAccountRead]:
    return InstagramAccountService(db).list_accounts(shop_id, current_user)


@router.post("/{shop_id}/instagram-accounts", response_model=InstagramAccountRead, status_code=201)
def create_instagram_account(
    shop_id: UUID,
    payload: InstagramAccountCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
) -> InstagramAccountRead:
    return InstagramAccountService(db).create_account(shop_id, payload, current_user)
