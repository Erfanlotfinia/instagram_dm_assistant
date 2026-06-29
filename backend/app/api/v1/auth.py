from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, rate_limit_login
from app.core.config import get_settings
from app.core.security import create_access_token
from app.db.session import get_db_session
from app.domain.models import User
from app.schemas.auth import ChangePasswordRequest, CsrfTokenResponse, LoginRequest, LoginResponse, UserProfileUpdate, UserRead
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.services.session_service import SessionService

router = APIRouter(prefix="/auth", tags=["auth"])
ACCESS_COOKIE = "__Host-modira_access"
REFRESH_COOKIE = "__Host-modira_refresh"
CSRF_COOKIE = "modira_csrf"


def _secure() -> bool:
    settings = get_settings()
    if settings.auth_cookie_secure is not None:
        return settings.auth_cookie_secure
    # __Host- prefixed cookies require Secure. Localhost is a secure context in
    # modern browsers, so this works for local HTTP dev (5173 → 8800).
    return True


def _set_access(response: Response, user_id: str) -> None:
    settings = get_settings()
    response.set_cookie(ACCESS_COOKIE, create_access_token(user_id), httponly=True, secure=_secure(), samesite="lax", path="/", max_age=settings.jwt_access_token_expire_minutes * 60)


def _set_refresh(response: Response, token: str) -> None:
    response.set_cookie(REFRESH_COOKIE, token, httponly=True, secure=_secure(), samesite="lax", path="/", max_age=get_settings().refresh_token_expire_days * 86400)


def _set_csrf(response: Response, token: str | None = None) -> str:
    import secrets

    value = token or secrets.token_urlsafe(32)
    response.set_cookie(CSRF_COOKIE, value, httponly=False, secure=_secure(), samesite="lax", path="/")
    return value


def _clear(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db_session)],
    _: Annotated[None, Depends(rate_limit_login)],
    token_only: bool = False,
) -> LoginResponse:
    settings = get_settings()
    user = AuthService(db).verify_credentials(payload)
    access_token = create_access_token(str(user.id))

    if token_only and not settings.is_production:
        AuditService(db).log(
            action="login",
            entity_type="user",
            actor_user_id=user.id,
            entity_id=str(user.id),
            metadata={"email": user.email, "swagger_token_only": True},
        )
        AuditService(db).commit()
        return LoginResponse(
            user=UserRead.model_validate(user),
            session_id="",
            access_token=access_token,
        )

    session, refresh_token = SessionService(db).create(
        user.id,
        request.headers.get("user-agent"),
        request.client.host if request.client else None,
    )
    _set_access(response, str(user.id))
    _set_refresh(response, refresh_token)
    csrf_token = _set_csrf(response)
    AuditService(db).log(
        action="login",
        entity_type="user",
        actor_user_id=user.id,
        entity_id=str(user.id),
        metadata={"email": user.email},
    )
    AuditService(db).commit()
    return LoginResponse(
        user=UserRead.model_validate(user),
        session_id=session.session_id,
        access_token=access_token,
        csrf_token=csrf_token,
    )


@router.post("/refresh", response_model=LoginResponse)
def refresh(request: Request, response: Response, db: Annotated[Session, Depends(get_db_session)]) -> LoginResponse:
    token = request.cookies.get(REFRESH_COOKIE)
    rotated = SessionService(db).rotate(token or "", request.headers.get("user-agent"), request.client.host if request.client else None)
    if rotated is None:
        _clear(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh session")
    session, refresh_token = rotated
    user = AuthService(db).users.get_by_id(session.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    _set_access(response, str(user.id))
    _set_refresh(response, refresh_token)
    csrf_token = _set_csrf(response)
    return LoginResponse(
        user=UserRead.model_validate(user),
        session_id=session.session_id,
        access_token=create_access_token(str(user.id)),
        csrf_token=csrf_token,
    )


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: Annotated[Session, Depends(get_db_session)]) -> Response:
    SessionService(db).revoke_by_token(request.cookies.get(REFRESH_COOKIE))
    _clear(response)
    return Response(status_code=204)


@router.get("/csrf", response_model=CsrfTokenResponse)
def csrf_token(request: Request, response: Response) -> CsrfTokenResponse:
    if not request.cookies.get(ACCESS_COOKIE):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    token = request.cookies.get(CSRF_COOKIE)
    if not token:
        token = _set_csrf(response)
    return CsrfTokenResponse(csrf_token=token)


@router.get("/me", response_model=UserRead)
def me(current_user: Annotated[User, Depends(get_current_user)]) -> UserRead:
    return UserRead.model_validate(current_user)


@router.patch("/me", response_model=UserRead)
def update_me(payload: UserProfileUpdate, current_user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db_session)]) -> UserRead:
    updated = AuthService(db).update_profile(current_user, payload)
    AuditService(db).log(action="profile_update", entity_type="user", actor_user_id=current_user.id, entity_id=str(current_user.id), metadata={"full_name": updated.full_name}); AuditService(db).commit()
    return updated


@router.post("/change-password", status_code=204)
def change_password(payload: ChangePasswordRequest, current_user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db_session)]) -> Response:
    AuthService(db).change_password(current_user, payload)
    AuditService(db).log(action="password_change", entity_type="user", actor_user_id=current_user.id, entity_id=str(current_user.id)); AuditService(db).commit()
    return Response(status_code=204)
