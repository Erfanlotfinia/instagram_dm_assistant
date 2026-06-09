from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_shop_membership
from app.db.session import get_db_session
from app.domain.models import User
from app.schemas.resolve import (
    ResolveProductRequest,
    ResolveProductResponse,
    ResolveVariantRequest,
    ResolveVariantResponse,
    ResolverFeedbackRead,
    ResolverFeedbackRequest,
    ResolverTraceRead,
)
from app.services.advanced_variant_resolver_service import AdvancedVariantResolverService
from app.services.catalog_product_search_service import CatalogProductSearchService
from app.services.resolver_feedback_service import ResolverFeedbackService
from app.services.resolver_trace_service import ResolverTraceService

router = APIRouter(prefix="/resolve", tags=["resolve"])


def _handle_resolve_error(exc: Exception) -> HTTPException:
    """Map provider failures to a clear 502 instead of a generic 500."""
    message = str(exc)
    if "OPENAI_API_KEY" in message or "OpenAI" in message or "embedding" in message.casefold():
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM/embedding provider error: {message}",
        )
    if "qdrant" in message.casefold():
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Vector index error: {message}",
        )
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=message)


@router.post("/product", response_model=ResolveProductResponse)
def resolve_product(
    payload: ResolveProductRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
) -> ResolveProductResponse:
    try:
        return CatalogProductSearchService(db).resolve_product(payload, current_user)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise _handle_resolve_error(exc) from exc


@router.post("/variant", response_model=ResolveVariantResponse)
def resolve_variant(
    payload: ResolveVariantRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
) -> ResolveVariantResponse:
    try:
        return AdvancedVariantResolverService(db).resolve_variant(payload, current_user)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise _handle_resolve_error(exc) from exc


@router.get("/{trace_id}", response_model=ResolverTraceRead)
def get_resolver_trace(
    trace_id: UUID,
    shop_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
    _: Annotated[None, Depends(get_shop_membership)],
) -> ResolverTraceRead:
    trace = ResolverTraceService(db).get_trace(shop_id, trace_id)
    if trace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trace not found")
    return trace


@router.post("/{trace_id}/feedback", response_model=ResolverFeedbackRead)
def submit_resolver_feedback(
    trace_id: UUID,
    payload: ResolverFeedbackRequest,
    shop_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
    _: Annotated[None, Depends(get_shop_membership)],
) -> ResolverFeedbackRead:
    return ResolverFeedbackService(db).submit_feedback(shop_id, trace_id, payload, current_user)
