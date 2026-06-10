from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_shop_membership
from app.db.session import get_db_session
from app.domain.models import ShopMember, User
from app.schemas.instagram_product_map import (
    InstagramProductMapCreate,
    InstagramProductMapRead,
    InstagramProductMapUpdate,
    ResolveInstagramProductRequest,
    ResolveInstagramProductResponse,
)
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate
from app.schemas.variant import VariantCreate, VariantRead, VariantUpdate
from app.services.instagram_product_resolver import InstagramProductResolver
from app.services.product_service import ProductService
from app.services.variant_service import VariantService

router = APIRouter(prefix="/shops", tags=["products"])


@router.get("/{shop_id}/products", response_model=list[ProductRead])
def list_products(
    shop_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
    db: Annotated[Session, Depends(get_db_session)],
) -> list[ProductRead]:
    return ProductService(db).list_products(shop_id, current_user)


@router.post("/{shop_id}/products", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(
    shop_id: UUID,
    payload: ProductCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
    db: Annotated[Session, Depends(get_db_session)],
) -> ProductRead:
    return ProductService(db).create_product(shop_id, payload, current_user)


@router.get("/{shop_id}/products/{product_id}", response_model=ProductRead)
def get_product(
    shop_id: UUID,
    product_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
) -> ProductRead:
    return ProductService(db).get_product(shop_id, product_id, current_user)


@router.patch("/{shop_id}/products/{product_id}", response_model=ProductRead)
def update_product(
    shop_id: UUID,
    product_id: UUID,
    payload: ProductUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
) -> ProductRead:
    return ProductService(db).update_product(shop_id, product_id, payload, current_user)


@router.delete("/{shop_id}/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    shop_id: UUID,
    product_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
) -> None:
    ProductService(db).delete_product(shop_id, product_id, current_user)


@router.get("/{shop_id}/products/{product_id}/variants", response_model=list[VariantRead])
def list_variants(
    shop_id: UUID,
    product_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
) -> list[VariantRead]:
    return VariantService(db).list_variants(shop_id, product_id, current_user)


@router.post(
    "/{shop_id}/products/{product_id}/variants",
    response_model=VariantRead,
    status_code=status.HTTP_201_CREATED,
)
def create_variant(
    shop_id: UUID,
    product_id: UUID,
    payload: VariantCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
) -> VariantRead:
    return VariantService(db).create_variant(shop_id, product_id, payload, current_user)


@router.patch("/{shop_id}/variants/{variant_id}", response_model=VariantRead)
def update_variant(
    shop_id: UUID,
    variant_id: UUID,
    payload: VariantUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
) -> VariantRead:
    return VariantService(db).update_variant(shop_id, variant_id, payload, current_user)




@router.delete("/{shop_id}/variants/{variant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_variant(
    shop_id: UUID,
    variant_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
) -> None:
    VariantService(db).delete_variant(shop_id, variant_id, current_user)

@router.get("/{shop_id}/instagram-product-maps", response_model=list[InstagramProductMapRead])
def list_instagram_product_maps(
    shop_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
) -> list[InstagramProductMapRead]:
    return InstagramProductResolver(db).list_maps(shop_id, current_user)


@router.post(
    "/{shop_id}/instagram-product-maps",
    response_model=InstagramProductMapRead,
    status_code=status.HTTP_201_CREATED,
)
def create_instagram_product_map(
    shop_id: UUID,
    payload: InstagramProductMapCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
) -> InstagramProductMapRead:
    return InstagramProductResolver(db).create_map(shop_id, payload, current_user)


@router.patch(
    "/{shop_id}/instagram-product-maps/{map_id}",
    response_model=InstagramProductMapRead,
)
def update_instagram_product_map(
    shop_id: UUID,
    map_id: UUID,
    payload: InstagramProductMapUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
) -> InstagramProductMapRead:
    return InstagramProductResolver(db).update_map(shop_id, map_id, payload, current_user)


@router.post("/{shop_id}/resolve-instagram-product", response_model=ResolveInstagramProductResponse)
def resolve_instagram_product(
    shop_id: UUID,
    payload: ResolveInstagramProductRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
) -> ResolveInstagramProductResponse:
    return InstagramProductResolver(db).resolve(shop_id, payload, current_user)
