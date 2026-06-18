from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import encrypt_secret
from app.domain.enums import ChannelAccountStatus, ChannelProvider, InstagramAccountStatus
from app.domain.models import ChannelAccount, InstagramAccount, User
from app.repositories.instagram_account_repository import InstagramAccountRepository
from app.schemas.instagram_account import InstagramAccountCreate, InstagramAccountRead
from app.services.shop_service import ShopService


class InstagramAccountService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.accounts = InstagramAccountRepository(db)
        self.shop_service = ShopService(db)

    def list_accounts(self, shop_id: UUID, user: User) -> list[InstagramAccountRead]:
        self.shop_service.get_shop(shop_id, user)
        accounts = self.accounts.list_for_shop(shop_id)
        return [InstagramAccountRead.model_validate(account) for account in accounts]

    def create_account(
        self,
        shop_id: UUID,
        payload: InstagramAccountCreate,
        user: User,
    ) -> InstagramAccountRead:
        self.shop_service.get_shop(shop_id, user)
        account = InstagramAccount(
            shop_id=shop_id,
            ig_user_id=payload.ig_user_id,
            page_id=payload.page_id,
            username=payload.username,
            access_token_encrypted=encrypt_secret(payload.access_token),
            token_expires_at=payload.token_expires_at,
            webhook_enabled=payload.webhook_enabled,
            status=InstagramAccountStatus.CONNECTED,
        )
        self.db.add(account)
        self.db.flush()
        self.db.add(
            ChannelAccount(
                shop_id=shop_id,
                provider=ChannelProvider.INSTAGRAM,
                display_name=payload.username,
                external_account_id=payload.ig_user_id,
                bot_username=payload.username,
                access_token_encrypted=account.access_token_encrypted,
                status=ChannelAccountStatus.CONNECTED,
                capabilities_json={
                    "supports_webhook": True,
                    "supports_text": True,
                    "supports_images": True,
                },
                settings_json={"legacy_instagram_account_id": str(account.id)},
            )
        )
        try:
            created = self.accounts.create(account)
        except IntegrityError as exc:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Instagram account already exists for this shop",
            ) from exc
        return InstagramAccountRead.model_validate(created)
