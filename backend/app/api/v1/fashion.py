from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_shop_membership
from app.db.session import get_db_session
from app.domain.models import ShopMember, User
from app.schemas.fashion import ColorAliasCreate, ColorAliasRead, NormalizeColorRequest, NormalizeSizeRequest, NormalizedValueRead, SizeAliasCreate, SizeAliasRead, SizeChartCreate, SizeChartRead, VariantResolverRequest, VariantResolverResult
from app.services.fashion_alias_service import FashionAliasService
from app.services.fashion_normalization import normalize_color, normalize_size
from app.services.variant_resolver import VariantResolver

router = APIRouter(prefix="/shops/{shop_id}/fashion", tags=["fashion"])


@router.post("/normalize-color", response_model=NormalizedValueRead)
def normalize_color_endpoint(shop_id: UUID, payload: NormalizeColorRequest, _user: Annotated[User, Depends(get_current_user)], _membership: Annotated[ShopMember, Depends(get_shop_membership)]) -> NormalizedValueRead:
    return NormalizedValueRead(**normalize_color(payload.raw_color).__dict__)


@router.post("/normalize-size", response_model=NormalizedValueRead)
def normalize_size_endpoint(shop_id: UUID, payload: NormalizeSizeRequest, _user: Annotated[User, Depends(get_current_user)], _membership: Annotated[ShopMember, Depends(get_shop_membership)]) -> NormalizedValueRead:
    return NormalizedValueRead(**normalize_size(payload.raw_size, category=payload.category, size_chart=payload.size_chart).__dict__)


@router.post("/resolve-variant", response_model=VariantResolverResult)
def resolve_variant_endpoint(shop_id: UUID, payload: VariantResolverRequest, _user: Annotated[User, Depends(get_current_user)], _membership: Annotated[ShopMember, Depends(get_shop_membership)], db: Annotated[Session, Depends(get_db_session)]) -> VariantResolverResult:
    return VariantResolver(db).resolve(shop_id=shop_id, product_id=payload.product_id, raw_color=payload.raw_color, raw_size=payload.raw_size, quantity=payload.quantity)


@router.get("/color-aliases", response_model=list[ColorAliasRead])
def list_color_aliases(shop_id: UUID, current_user: Annotated[User, Depends(get_current_user)], _membership: Annotated[ShopMember, Depends(get_shop_membership)], db: Annotated[Session, Depends(get_db_session)]) -> list[ColorAliasRead]:
    return FashionAliasService(db).list_color_aliases(shop_id, current_user)


@router.post("/color-aliases", response_model=ColorAliasRead, status_code=201)
def create_color_alias(shop_id: UUID, payload: ColorAliasCreate, current_user: Annotated[User, Depends(get_current_user)], _membership: Annotated[ShopMember, Depends(get_shop_membership)], db: Annotated[Session, Depends(get_db_session)]) -> ColorAliasRead:
    return FashionAliasService(db).create_color_alias(shop_id, payload.raw_value, payload.normalized_value, payload.language, current_user)


@router.get("/size-aliases", response_model=list[SizeAliasRead])
def list_size_aliases(shop_id: UUID, current_user: Annotated[User, Depends(get_current_user)], _membership: Annotated[ShopMember, Depends(get_shop_membership)], db: Annotated[Session, Depends(get_db_session)]) -> list[SizeAliasRead]:
    return FashionAliasService(db).list_size_aliases(shop_id, current_user)


@router.post("/size-aliases", response_model=SizeAliasRead, status_code=201)
def create_size_alias(shop_id: UUID, payload: SizeAliasCreate, current_user: Annotated[User, Depends(get_current_user)], _membership: Annotated[ShopMember, Depends(get_shop_membership)], db: Annotated[Session, Depends(get_db_session)]) -> SizeAliasRead:
    return FashionAliasService(db).create_size_alias(shop_id, payload.raw_value, payload.normalized_value, payload.category, current_user)


@router.get("/size-charts", response_model=list[SizeChartRead])
def list_size_charts(shop_id: UUID, current_user: Annotated[User, Depends(get_current_user)], _membership: Annotated[ShopMember, Depends(get_shop_membership)], db: Annotated[Session, Depends(get_db_session)]) -> list[SizeChartRead]:
    return FashionAliasService(db).list_size_charts(shop_id, current_user)


@router.post("/size-charts", response_model=SizeChartRead, status_code=201)
def create_size_chart(shop_id: UUID, payload: SizeChartCreate, current_user: Annotated[User, Depends(get_current_user)], _membership: Annotated[ShopMember, Depends(get_shop_membership)], db: Annotated[Session, Depends(get_db_session)]) -> SizeChartRead:
    return FashionAliasService(db).create_size_chart(shop_id, payload.product_id, payload.category, payload.chart_json, current_user)
