from uuid import UUID

import jwt
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_secret, verify_secret
from app.domain.enums import UserRole
from app.domain.models import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import ChangePasswordRequest, LoginRequest, TokenResponse, UserProfileUpdate, UserRead


class AuthService:
    def __init__(self, db: Session) -> None:
        self.users = UserRepository(db)

    def verify_credentials(self, payload: LoginRequest) -> User:
        user = self.users.get_by_email(payload.email.lower())
        if user is None or not verify_secret(payload.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive",
            )
        return user

    def authenticate(self, payload: LoginRequest) -> TokenResponse:
        user = self.verify_credentials(payload)
        token = create_access_token(str(user.id))
        return TokenResponse(access_token=token)

    def get_user_from_token(self, token: str) -> User:
        from app.core.security import decode_access_token

        try:
            payload = decode_access_token(token)
        except jwt.PyJWTError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            ) from exc

        subject = payload.get("sub")
        if subject is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )

        user = self.users.get_by_id(UUID(subject))
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )
        return user

    def get_current_user_read(self, user: User) -> UserRead:
        return UserRead.model_validate(user)

    def update_profile(self, user: User, payload: UserProfileUpdate) -> UserRead:
        user.full_name = payload.full_name.strip()
        updated = self.users.save(user)
        return UserRead.model_validate(updated)

    def change_password(self, user: User, payload: ChangePasswordRequest) -> None:
        if not verify_secret(payload.current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect",
            )
        if payload.current_password == payload.new_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be different from the current password",
            )
        user.password_hash = hash_secret(payload.new_password)
        self.users.save(user)

    @staticmethod
    def create_user(
        db: Session,
        *,
        email: str,
        password: str,
        full_name: str,
        role: UserRole,
    ) -> User:
        repo = UserRepository(db)
        user = User(
            email=email.lower(),
            password_hash=hash_secret(password),
            full_name=full_name,
            role=role,
            is_active=True,
        )
        return repo.create(user)
