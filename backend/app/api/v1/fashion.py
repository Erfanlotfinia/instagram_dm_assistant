from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_shop_membership
from app.db.session import get_db_session
from app.domain.models import ShopMember, User
from app.schemas.fashion import NormalizeColorRequest, NormalizeSizeRequest, NormalizedValueRead, VariantResolverRequest, VariantResolverResult
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
    return VariantResolver(db).resolve(product_id=payload.product_id, raw_color=payload.raw_color, raw_size=payload.raw_size, quantity=payload.quantity)
