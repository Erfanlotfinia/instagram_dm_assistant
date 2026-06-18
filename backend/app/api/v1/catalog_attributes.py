from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_shop_membership
from app.db.session import get_db_session
from app.domain.models import ShopMember, User
from app.schemas.fashion import (
    ColorAliasCreate,
    ColorAliasRead,
    ColorAliasUpdate,
    NormalizeColorRequest,
    NormalizeSizeRequest,
    NormalizedValueRead,
    SizeAliasCreate,
    SizeAliasRead,
    SizeAliasUpdate,
    SizeChartCreate,
    SizeChartRead,
    UnavailableDemandRead,
    VariantResolverRequest,
    VariantResolverResult,
    AttributeAliasCreate,
    AttributeAliasRead,
)
from app.services.attribute_dictionary_service import AttributeDictionaryService
from app.services.fashion_normalization import ColorNormalizer, SizeNormalizer
from app.services.generic_variant_resolver import GenericVariantResolver
from app.services.variant_resolver import VariantResolver

router = APIRouter(prefix="/shops/{shop_id}", tags=["catalog attributes"])


def _normalized_read(result) -> NormalizedValueRead:
    return NormalizedValueRead(
        raw=result.raw_value,
        normalized=result.normalized_value,
        raw_value=result.raw_value,
        normalized_value=result.normalized_value,
        matched=result.matched,
        confidence=result.confidence,
        source=result.source,
    )


@router.post("/fashion/normalize-color", response_model=NormalizedValueRead)
def normalize_color_endpoint(shop_id: UUID, payload: NormalizeColorRequest, _user: Annotated[User, Depends(get_current_user)], _membership: Annotated[ShopMember, Depends(get_shop_membership)], db: Annotated[Session, Depends(get_db_session)]) -> NormalizedValueRead:
    return _normalized_read(ColorNormalizer(db).normalize(shop_id, payload.raw_color))


@router.post("/fashion/normalize-size", response_model=NormalizedValueRead)
def normalize_size_endpoint(shop_id: UUID, payload: NormalizeSizeRequest, _user: Annotated[User, Depends(get_current_user)], _membership: Annotated[ShopMember, Depends(get_shop_membership)], db: Annotated[Session, Depends(get_db_session)]) -> NormalizedValueRead:
    return _normalized_read(SizeNormalizer(db).normalize(shop_id, payload.raw_size, category=payload.category, size_chart=payload.size_chart))


@router.post("/fashion/resolve-variant", response_model=VariantResolverResult)
@router.post("/variant-resolver/test", response_model=VariantResolverResult)
def resolve_variant_endpoint(shop_id: UUID, payload: VariantResolverRequest, _user: Annotated[User, Depends(get_current_user)], _membership: Annotated[ShopMember, Depends(get_shop_membership)], db: Annotated[Session, Depends(get_db_session)]) -> VariantResolverResult:
    if payload.raw_requested_attributes:
        return GenericVariantResolver(db).resolve(shop_id=shop_id, product_id=payload.product_id, raw_requested_attributes=payload.raw_requested_attributes, quantity=payload.quantity)
    return VariantResolver(db).resolve(shop_id=shop_id, product_id=payload.product_id, raw_color=payload.raw_color, raw_size=payload.raw_size, quantity=payload.quantity)


@router.get("/color-aliases", response_model=list[ColorAliasRead])
@router.get("/fashion/color-aliases", response_model=list[ColorAliasRead])
def list_color_aliases(shop_id: UUID, current_user: Annotated[User, Depends(get_current_user)], _membership: Annotated[ShopMember, Depends(get_shop_membership)], db: Annotated[Session, Depends(get_db_session)]) -> list[ColorAliasRead]:
    return AttributeDictionaryService(db).list_color_aliases(shop_id, current_user)


@router.post("/color-aliases", response_model=ColorAliasRead, status_code=201)
@router.post("/fashion/color-aliases", response_model=ColorAliasRead, status_code=201)
def create_color_alias(shop_id: UUID, payload: ColorAliasCreate, current_user: Annotated[User, Depends(get_current_user)], _membership: Annotated[ShopMember, Depends(get_shop_membership)], db: Annotated[Session, Depends(get_db_session)]) -> ColorAliasRead:
    return AttributeDictionaryService(db).create_color_alias(shop_id, payload.raw_value, payload.normalized_value, payload.language, current_user)


@router.patch("/color-aliases/{alias_id}", response_model=ColorAliasRead)
def update_color_alias(shop_id: UUID, alias_id: UUID, payload: ColorAliasUpdate, current_user: Annotated[User, Depends(get_current_user)], _membership: Annotated[ShopMember, Depends(get_shop_membership)], db: Annotated[Session, Depends(get_db_session)]) -> ColorAliasRead:
    return AttributeDictionaryService(db).update_color_alias(shop_id, alias_id, current_user, **payload.model_dump(exclude_unset=True))


@router.delete("/color-aliases/{alias_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_color_alias(shop_id: UUID, alias_id: UUID, current_user: Annotated[User, Depends(get_current_user)], _membership: Annotated[ShopMember, Depends(get_shop_membership)], db: Annotated[Session, Depends(get_db_session)]) -> Response:
    AttributeDictionaryService(db).delete_color_alias(shop_id, alias_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/size-aliases", response_model=list[SizeAliasRead])
@router.get("/fashion/size-aliases", response_model=list[SizeAliasRead])
def list_size_aliases(shop_id: UUID, current_user: Annotated[User, Depends(get_current_user)], _membership: Annotated[ShopMember, Depends(get_shop_membership)], db: Annotated[Session, Depends(get_db_session)]) -> list[SizeAliasRead]:
    return AttributeDictionaryService(db).list_size_aliases(shop_id, current_user)


@router.post("/size-aliases", response_model=SizeAliasRead, status_code=201)
@router.post("/fashion/size-aliases", response_model=SizeAliasRead, status_code=201)
def create_size_alias(shop_id: UUID, payload: SizeAliasCreate, current_user: Annotated[User, Depends(get_current_user)], _membership: Annotated[ShopMember, Depends(get_shop_membership)], db: Annotated[Session, Depends(get_db_session)]) -> SizeAliasRead:
    return AttributeDictionaryService(db).create_size_alias(shop_id, payload.raw_value, payload.normalized_value, payload.category, current_user)


@router.patch("/size-aliases/{alias_id}", response_model=SizeAliasRead)
def update_size_alias(shop_id: UUID, alias_id: UUID, payload: SizeAliasUpdate, current_user: Annotated[User, Depends(get_current_user)], _membership: Annotated[ShopMember, Depends(get_shop_membership)], db: Annotated[Session, Depends(get_db_session)]) -> SizeAliasRead:
    return AttributeDictionaryService(db).update_size_alias(shop_id, alias_id, current_user, **payload.model_dump(exclude_unset=True))


@router.delete("/size-aliases/{alias_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_size_alias(shop_id: UUID, alias_id: UUID, current_user: Annotated[User, Depends(get_current_user)], _membership: Annotated[ShopMember, Depends(get_shop_membership)], db: Annotated[Session, Depends(get_db_session)]) -> Response:
    AttributeDictionaryService(db).delete_size_alias(shop_id, alias_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/unavailable-demand", response_model=list[UnavailableDemandRead])
def list_unavailable_demand(shop_id: UUID, current_user: Annotated[User, Depends(get_current_user)], _membership: Annotated[ShopMember, Depends(get_shop_membership)], db: Annotated[Session, Depends(get_db_session)]) -> list[UnavailableDemandRead]:
    return AttributeDictionaryService(db).list_unavailable_demand(shop_id, current_user)


@router.get("/fashion/size-charts", response_model=list[SizeChartRead])
def list_size_charts(shop_id: UUID, current_user: Annotated[User, Depends(get_current_user)], _membership: Annotated[ShopMember, Depends(get_shop_membership)], db: Annotated[Session, Depends(get_db_session)]) -> list[SizeChartRead]:
    return AttributeDictionaryService(db).list_size_charts(shop_id, current_user)


@router.post("/fashion/size-charts", response_model=SizeChartRead, status_code=201)
def create_size_chart(shop_id: UUID, payload: SizeChartCreate, current_user: Annotated[User, Depends(get_current_user)], _membership: Annotated[ShopMember, Depends(get_shop_membership)], db: Annotated[Session, Depends(get_db_session)]) -> SizeChartRead:
    return AttributeDictionaryService(db).create_size_chart(shop_id, payload.product_id, payload.category, payload.chart_json, current_user)


@router.get("/attribute-aliases", response_model=list[AttributeAliasRead])
def list_attribute_aliases(shop_id: UUID, current_user: Annotated[User, Depends(get_current_user)], _membership: Annotated[ShopMember, Depends(get_shop_membership)], db: Annotated[Session, Depends(get_db_session)]) -> list[AttributeAliasRead]:
    return AttributeDictionaryService(db).list_attribute_aliases(shop_id, current_user)


@router.post("/attribute-aliases", response_model=AttributeAliasRead, status_code=201)
def create_attribute_alias(shop_id: UUID, payload: AttributeAliasCreate, current_user: Annotated[User, Depends(get_current_user)], _membership: Annotated[ShopMember, Depends(get_shop_membership)], db: Annotated[Session, Depends(get_db_session)]) -> AttributeAliasRead:
    return AttributeDictionaryService(db).create_attribute_alias(shop_id, payload.attribute_slug, payload.raw_value, payload.normalized_value, payload.language, current_user)
