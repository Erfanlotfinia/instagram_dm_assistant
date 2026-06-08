from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_shop_membership, require_shop_role
from app.db.session import get_db_session
from app.domain.enums import UserRole
from app.domain.models import ShopMember, User
from app.schemas.upsell import ProductUpsellCreate, ProductUpsellRead, ProductUpsellUpdate
from app.services.upsell_service import UpsellService

router = APIRouter(prefix="/shops/{shop_id}/product-upsells", tags=["upsells"])


@router.get("", response_model=list[ProductUpsellRead])
def list_product_upsells(
    shop_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
    db: Annotated[Session, Depends(get_db_session)],
) -> list[ProductUpsellRead]:
    rules = UpsellService(db).list_rules(shop_id, current_user)
    return [ProductUpsellRead.model_validate(rule) for rule in rules]


@router.post("", response_model=ProductUpsellRead, status_code=201)
def create_product_upsell(
    shop_id: UUID,
    payload: ProductUpsellCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    _: Annotated[ShopMember, Depends(require_shop_role(UserRole.OPERATOR))],
    db: Annotated[Session, Depends(get_db_session)],
) -> ProductUpsellRead:
    rule = UpsellService(db).create_rule(shop_id, payload, current_user)
    return ProductUpsellRead.model_validate(rule)


@router.patch("/{upsell_id}", response_model=ProductUpsellRead)
def update_product_upsell(
    shop_id: UUID,
    upsell_id: UUID,
    payload: ProductUpsellUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    _: Annotated[ShopMember, Depends(require_shop_role(UserRole.OPERATOR))],
    db: Annotated[Session, Depends(get_db_session)],
) -> ProductUpsellRead:
    rule = UpsellService(db).update_rule(shop_id, upsell_id, payload, current_user)
    return ProductUpsellRead.model_validate(rule)


@router.delete("/{upsell_id}", status_code=204)
def delete_product_upsell(
    shop_id: UUID,
    upsell_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _: Annotated[ShopMember, Depends(require_shop_role(UserRole.OPERATOR))],
    db: Annotated[Session, Depends(get_db_session)],
) -> Response:
    UpsellService(db).delete_rule(shop_id, upsell_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
