from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_shop_membership
from app.core.analytics_dates import resolve_analytics_range
from app.db.session import get_db_session
from app.domain.models import ShopMember, User
from app.schemas.analytics import (
    AgentPerformanceMetrics,
    FunnelAnalytics,
    HandoffAnalyticsRow,
    LostDemandListResponse,
    OperatorPerformanceListResponse,
    PostPerformanceRow,
    PostRevenueRow,
    ResponseTimeAnalytics,
    StockDemandRow,
    UnavailableDemandRow,
)
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/shops/{shop_id}/analytics", tags=["analytics"])


def _date_range(
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
) -> tuple[datetime | None, datetime | None]:
    return resolve_analytics_range(date_from=date_from, date_to=date_to, start=start, end=end)


@router.get("/funnel", response_model=FunnelAnalytics)
def funnel(
    shop_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
    db: Annotated[Session, Depends(get_db_session)],
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
) -> FunnelAnalytics:
    range_start, range_end = _date_range(date_from, date_to, start, end)
    return AnalyticsService(db).funnel(shop_id, current_user, range_start, range_end)


@router.get("/posts", response_model=list[PostPerformanceRow])
def posts(
    shop_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
    db: Annotated[Session, Depends(get_db_session)],
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[PostPerformanceRow]:
    range_start, range_end = _date_range(date_from, date_to, start, end)
    return AnalyticsService(db).posts(shop_id, current_user, range_start, range_end)


@router.get("/post-revenue", response_model=list[PostRevenueRow])
def post_revenue(
    shop_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
    db: Annotated[Session, Depends(get_db_session)],
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[PostRevenueRow]:
    range_start, range_end = _date_range(date_from, date_to, start, end)
    return AnalyticsService(db).post_revenue(shop_id, current_user, range_start, range_end)


@router.get("/stock-demand", response_model=list[StockDemandRow])
def stock_demand(
    shop_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
    db: Annotated[Session, Depends(get_db_session)],
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[StockDemandRow]:
    range_start, range_end = _date_range(date_from, date_to, start, end)
    return AnalyticsService(db).stock_demand(shop_id, current_user, range_start, range_end)


@router.get("/handoff", response_model=list[HandoffAnalyticsRow])
def handoff(
    shop_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
    db: Annotated[Session, Depends(get_db_session)],
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[HandoffAnalyticsRow]:
    range_start, range_end = _date_range(date_from, date_to, start, end)
    return AnalyticsService(db).handoff(shop_id, current_user, range_start, range_end)


@router.get("/unavailable-demand", response_model=list[UnavailableDemandRow])
def unavailable_demand(
    shop_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
    db: Annotated[Session, Depends(get_db_session)],
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[UnavailableDemandRow]:
    range_start, range_end = _date_range(date_from, date_to, start, end)
    return AnalyticsService(db).unavailable_demand(shop_id, current_user, range_start, range_end)


@router.get("/lost-demand", response_model=LostDemandListResponse)
def lost_demand(
    shop_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
    db: Annotated[Session, Depends(get_db_session)],
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
) -> LostDemandListResponse:
    range_start, range_end = _date_range(date_from, date_to, start, end)
    return AnalyticsService(db).lost_demand(
        shop_id,
        current_user,
        range_start,
        range_end,
        page=page,
        page_size=page_size,
    )


@router.get("/operator-performance", response_model=OperatorPerformanceListResponse)
def operator_performance(
    shop_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
    db: Annotated[Session, Depends(get_db_session)],
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
) -> OperatorPerformanceListResponse:
    range_start, range_end = _date_range(date_from, date_to, start, end)
    return AnalyticsService(db).operator_performance(
        shop_id,
        current_user,
        range_start,
        range_end,
        page=page,
        page_size=page_size,
    )


@router.get("/agent-performance", response_model=AgentPerformanceMetrics)
def agent_performance(
    shop_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
    db: Annotated[Session, Depends(get_db_session)],
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
) -> AgentPerformanceMetrics:
    range_start, range_end = _date_range(date_from, date_to, start, end)
    return AnalyticsService(db).agent_performance(shop_id, current_user, range_start, range_end)


@router.get("/response-time", response_model=ResponseTimeAnalytics)
def response_time(
    shop_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
    db: Annotated[Session, Depends(get_db_session)],
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
) -> ResponseTimeAnalytics:
    range_start, range_end = _date_range(date_from, date_to, start, end)
    return AnalyticsService(db).response_time(shop_id, current_user, range_start, range_end)
