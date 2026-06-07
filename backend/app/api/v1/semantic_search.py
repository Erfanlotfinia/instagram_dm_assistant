from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_minimum_role
from app.db.session import get_db_session
from app.domain.enums import UserRole
from app.domain.models import User
from app.schemas.agent import SemanticSearchRequest, SemanticSearchResponse
from app.services.product_semantic_search_service import ProductSemanticSearchService

router = APIRouter(prefix="/shops/{shop_id}/semantic-search", tags=["semantic-search"])


@router.post("", response_model=SemanticSearchResponse)
def semantic_product_search(
    shop_id: UUID,
    payload: SemanticSearchRequest,
    current_user: Annotated[User, Depends(require_minimum_role(UserRole.ADMIN))],
    db: Annotated[Session, Depends(get_db_session)],
) -> SemanticSearchResponse:
    return ProductSemanticSearchService(db).search_for_shop(shop_id, payload, current_user)
