from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_shop_membership
from app.db.session import get_db_session
from app.domain.models import User
from app.schemas.catalog import (
    CatalogImportJobRead,
    CatalogImportRequest,
    CatalogProductListResponse,
    CatalogReindexJobRead,
    CatalogReindexRequest,
    ProductAliasesPatchRequest,
    ProductAliasesPatchResponse,
)
from app.services.catalog_import_service import CatalogImportService
from app.services.catalog_reindex_service import CatalogReindexService
from app.services.catalog_service import CatalogService
from app.services.shop_service import ShopService

router = APIRouter(prefix="/catalog", tags=["catalog"])


def _handle_catalog_error(exc: Exception) -> HTTPException:
    """Map provider/index failures to a clear 502 instead of a generic 500."""
    message = str(exc)
    if "OPENAI_API_KEY" in message or "embedding" in message.casefold():
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Embedding provider error: {message}",
        )
    if "qdrant" in message.casefold():
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Vector index error: {message}",
        )
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=message)


@router.post("/import", response_model=CatalogImportJobRead)
def import_catalog(
    payload: CatalogImportRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
) -> CatalogImportJobRead:
    ShopService(db).get_shop(payload.shop_id, current_user)
    return CatalogImportService(db).import_catalog(payload, current_user)


@router.post("/reindex", response_model=CatalogReindexJobRead)
def reindex_catalog(
    payload: CatalogReindexRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
) -> CatalogReindexJobRead:
    ShopService(db).get_shop(payload.shop_id, current_user)
    try:
        return CatalogReindexService(db).reindex(payload, current_user)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise _handle_catalog_error(exc) from exc


@router.get("/products", response_model=CatalogProductListResponse)
def list_catalog_products(
    shop_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
    _: Annotated[None, Depends(get_shop_membership)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None),
) -> CatalogProductListResponse:
    return CatalogService(db).list_products(shop_id, current_user, page=page, page_size=page_size, search=search)


@router.patch("/products/{product_id}/aliases", response_model=ProductAliasesPatchResponse)
def patch_product_aliases(
    product_id: UUID,
    payload: ProductAliasesPatchRequest,
    shop_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
    _: Annotated[None, Depends(get_shop_membership)],
) -> ProductAliasesPatchResponse:
    return CatalogService(db).patch_aliases(shop_id, product_id, payload, current_user)
