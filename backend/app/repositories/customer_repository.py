from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import ChannelProvider
from app.domain.models import ChannelContactIdentity, Customer


class CustomerRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, customer_id: UUID) -> Customer | None:
        return self.db.get(Customer, customer_id)

    def get_by_instagram_user_id(self, shop_id: UUID, instagram_user_id: str) -> Customer | None:
        return self.get_customer_by_channel_identity(
            shop_id, ChannelProvider.INSTAGRAM, instagram_user_id
        )

    def get_customer_by_channel_identity(
        self,
        shop_id: UUID,
        provider: ChannelProvider,
        external_user_id: str,
    ) -> Customer | None:
        stmt = (
            select(Customer)
            .join(ChannelContactIdentity, ChannelContactIdentity.customer_id == Customer.id)
            .where(
                ChannelContactIdentity.shop_id == shop_id,
                ChannelContactIdentity.provider == provider,
                ChannelContactIdentity.external_user_id == external_user_id,
            )
        )
        return self.db.scalar(stmt)

    def get_or_create_channel_contact_identity(
        self,
        *,
        shop_id: UUID,
        customer_id: UUID,
        provider: ChannelProvider,
        channel_account_id: UUID,
        external_user_id: str,
        external_chat_id: str | None = None,
        username: str | None = None,
        display_name: str | None = None,
        phone: str | None = None,
        raw_profile_json: dict | None = None,
    ) -> ChannelContactIdentity:
        identity = self.db.scalar(
            select(ChannelContactIdentity).where(
                ChannelContactIdentity.shop_id == shop_id,
                ChannelContactIdentity.provider == provider,
                ChannelContactIdentity.channel_account_id == channel_account_id,
                ChannelContactIdentity.external_user_id == external_user_id,
            )
        )
        if identity is not None:
            return identity
        identity = ChannelContactIdentity(
            shop_id=shop_id,
            customer_id=customer_id,
            provider=provider,
            channel_account_id=channel_account_id,
            external_user_id=external_user_id,
            external_chat_id=external_chat_id,
            username=username,
            display_name=display_name,
            phone=phone,
            raw_profile_json=raw_profile_json,
        )
        self.db.add(identity)
        self.db.flush()
        return identity

    def create_customer_from_channel_identity(
        self,
        *,
        shop_id: UUID,
        provider: ChannelProvider,
        channel_account_id: UUID,
        external_user_id: str,
        external_chat_id: str | None = None,
        display_name: str | None = None,
        username: str | None = None,
        phone: str | None = None,
        email: str | None = None,
        raw_profile_json: dict | None = None,
    ) -> Customer:
        existing = self.get_customer_by_channel_identity(shop_id, provider, external_user_id)
        if existing is not None:
            self.get_or_create_channel_contact_identity(
                shop_id=shop_id,
                customer_id=existing.id,
                provider=provider,
                channel_account_id=channel_account_id,
                external_user_id=external_user_id,
                external_chat_id=external_chat_id,
            )
            return existing
        customer = Customer(
            shop_id=shop_id,
            display_name=display_name or username,
            phone=phone,
            email=email,
            primary_channel_provider=provider,
            primary_external_user_id=external_user_id,
        )
        self.create(customer)
        self.get_or_create_channel_contact_identity(
            shop_id=shop_id,
            customer_id=customer.id,
            provider=provider,
            channel_account_id=channel_account_id,
            external_user_id=external_user_id,
            external_chat_id=external_chat_id,
            username=username,
            display_name=display_name,
            phone=phone,
            raw_profile_json=raw_profile_json,
        )
        return customer

    def create(self, customer: Customer) -> Customer:
        self.db.add(customer)
        self.db.flush()
        return customer
