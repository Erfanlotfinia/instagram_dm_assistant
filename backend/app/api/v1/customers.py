from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_shop_membership, require_shop_role
from app.db.session import get_db_session
from app.domain.enums import UserRole
from app.domain.models import ShopMember, User
from app.schemas.customer import CustomerProfileRead, CustomerUpdate
from app.schemas.customer_preferences import CustomerPreferencesRead
from app.services.customer_preferences_service import CustomerPreferencesService
from app.services.customer_service import CustomerService

router = APIRouter(prefix="/shops/{shop_id}/customers", tags=["customers"])


@router.get("/{customer_id}", response_model=CustomerProfileRead)
def get_customer_profile(
    shop_id: UUID,
    customer_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
    db: Annotated[Session, Depends(get_db_session)],
) -> CustomerProfileRead:
    return CustomerService(db).get_profile(shop_id, customer_id, current_user)


@router.get("/{customer_id}/preferences", response_model=CustomerPreferencesRead)
def get_customer_preferences(
    shop_id: UUID,
    customer_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
    db: Annotated[Session, Depends(get_db_session)],
) -> CustomerPreferencesRead:
    from fastapi import HTTPException, status
    from app.repositories.customer_repository import CustomerRepository

    prefs = CustomerPreferencesService(db).get_preferences(shop_id, customer_id, current_user)
    if prefs is None:
        customer = CustomerRepository(db).get_by_id(customer_id)
        if customer is None or customer.shop_id != shop_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
        prefs = CustomerPreferencesService(db).get_or_create(customer_id)
    return CustomerPreferencesService.to_read(prefs)


@router.patch("/{customer_id}", response_model=CustomerProfileRead)
def update_customer_profile(
    shop_id: UUID,
    customer_id: UUID,
    payload: CustomerUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.OPERATOR))],
    db: Annotated[Session, Depends(get_db_session)],
) -> CustomerProfileRead:
    return CustomerService(db).update_customer(shop_id, customer_id, current_user, payload)
