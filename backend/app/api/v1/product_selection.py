from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_shop_membership
from app.db.session import get_db_session
from app.domain.models import ShopMember, User
from app.services.product_selection_service import ProductSelectionService

router = APIRouter(prefix="/shops/{shop_id}/conversations", tags=["product-selection"])


class ProductSelectionRequest(BaseModel):
    product_id: UUID


@router.post("/{conversation_id}/select-product")
def select_product(shop_id: UUID, conversation_id: UUID, payload: ProductSelectionRequest, _user: Annotated[User, Depends(get_current_user)], _membership: Annotated[ShopMember, Depends(get_shop_membership)], db: Annotated[Session, Depends(get_db_session)]) -> dict:
    ProductSelectionService(db).select_product(shop_id, conversation_id, payload.product_id)
    return {"conversation_id": str(conversation_id), "selected_product_id": str(payload.product_id)}
