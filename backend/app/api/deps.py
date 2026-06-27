from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.rate_limit import RateLimitRule, enforce_rate_limit
from app.core.roles import has_minimum_role
from app.db.session import get_db_session
from app.domain.enums import UserRole
from app.domain.models import ShopMember, User
from app.services.auth_service import AuthService
from app.services.shop_service import ShopService

bearer_scheme = HTTPBearer(auto_error=False)


def rate_limit_login(
    request: Request,
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    enforce_rate_limit(
        request,
        RateLimitRule("login", settings.rate_limit_login_per_minute, 60),
        response,
        settings=settings,
    )


def rate_limit_webhook(
    request: Request,
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    enforce_rate_limit(
        request,
        RateLimitRule("webhook", settings.rate_limit_webhook_per_minute, 60),
        response,
        settings=settings,
    )


def rate_limit_outbound_message(
    request: Request,
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    enforce_rate_limit(
        request,
        RateLimitRule("outbound_message", settings.rate_limit_outbound_message_per_minute, 60),
        response,
        settings=settings,
    )


def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db_session)],
) -> User:
    token = request.cookies.get("__Host-modira_access")
    if not token and credentials is not None and credentials.scheme.lower() == "bearer":
        token = credentials.credentials
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return AuthService(db).get_user_from_token(token)


def get_shop_membership(
    shop_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
) -> ShopMember:
    membership = ShopService(db).get_membership(shop_id, current_user.id)
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this shop",
        )
    return membership


def require_shop_role(required_role: UserRole):
    def _dependency(
        membership: Annotated[ShopMember, Depends(get_shop_membership)],
    ) -> ShopMember:
        if not has_minimum_role(membership.role, required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {required_role.value} role or higher",
            )
        return membership

    return _dependency


def require_minimum_role(required_role: UserRole):
    def _dependency(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if not has_minimum_role(current_user.role, required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {required_role.value} role or higher",
            )
        return current_user

    return _dependency
