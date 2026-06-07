from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_shop_membership
from app.db.session import get_db_session
from app.domain.models import ShopMember, User
from app.schemas.analytics import FunnelAnalytics, HandoffAnalyticsRow, PostPerformanceRow, StockDemandRow
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/shops/{shop_id}/analytics", tags=["analytics"])


@router.get("/funnel", response_model=FunnelAnalytics)
def funnel(shop_id: UUID, current_user: Annotated[User, Depends(get_current_user)], _membership: Annotated[ShopMember, Depends(get_shop_membership)], db: Annotated[Session, Depends(get_db_session)], start: datetime | None = None, end: datetime | None = None) -> FunnelAnalytics:
    return AnalyticsService(db).funnel(shop_id, current_user, start, end)


@router.get("/posts", response_model=list[PostPerformanceRow])
def posts(shop_id: UUID, current_user: Annotated[User, Depends(get_current_user)], _membership: Annotated[ShopMember, Depends(get_shop_membership)], db: Annotated[Session, Depends(get_db_session)], start: datetime | None = None, end: datetime | None = None) -> list[PostPerformanceRow]:
    return AnalyticsService(db).posts(shop_id, current_user, start, end)


@router.get("/stock-demand", response_model=list[StockDemandRow])
def stock_demand(shop_id: UUID, current_user: Annotated[User, Depends(get_current_user)], _membership: Annotated[ShopMember, Depends(get_shop_membership)], db: Annotated[Session, Depends(get_db_session)], start: datetime | None = None, end: datetime | None = None) -> list[StockDemandRow]:
    return AnalyticsService(db).stock_demand(shop_id, current_user, start, end)


@router.get("/handoff", response_model=list[HandoffAnalyticsRow])
def handoff(shop_id: UUID, current_user: Annotated[User, Depends(get_current_user)], _membership: Annotated[ShopMember, Depends(get_shop_membership)], db: Annotated[Session, Depends(get_db_session)], start: datetime | None = None, end: datetime | None = None) -> list[HandoffAnalyticsRow]:
    return AnalyticsService(db).handoff(shop_id, current_user, start, end)
