from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, rate_limit_login
from app.db.session import get_db_session
from app.domain.models import User
from app.schemas.auth import ChangePasswordRequest, LoginRequest, TokenResponse, UserProfileUpdate, UserRead
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    db: Annotated[Session, Depends(get_db_session)],
    _: Annotated[None, Depends(rate_limit_login)],
) -> TokenResponse:
    result = AuthService(db).authenticate(payload)
    user = AuthService(db).users.get_by_email(payload.email.lower())
    if user is not None:
        AuditService(db).log(
            action="login",
            entity_type="user",
            actor_user_id=user.id,
            entity_id=str(user.id),
            metadata={"email": user.email},
        )
        AuditService(db).commit()
    return result


@router.get("/me", response_model=UserRead)
def me(current_user: Annotated[User, Depends(get_current_user)]) -> UserRead:
    return UserRead.model_validate(current_user)


@router.patch("/me", response_model=UserRead)
def update_me(
    payload: UserProfileUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
) -> UserRead:
    service = AuthService(db)
    updated = service.update_profile(current_user, payload)
    AuditService(db).log(
        action="profile_update",
        entity_type="user",
        actor_user_id=current_user.id,
        entity_id=str(current_user.id),
        metadata={"full_name": updated.full_name},
    )
    AuditService(db).commit()
    return updated


@router.post("/change-password", status_code=204)
def change_password(
    payload: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
) -> Response:
    AuthService(db).change_password(current_user, payload)
    AuditService(db).log(
        action="password_change",
        entity_type="user",
        actor_user_id=current_user.id,
        entity_id=str(current_user.id),
    )
    AuditService(db).commit()
    return Response(status_code=204)
