from uuid import uuid4

import pytest

from app.domain.enums import ChannelAccountStatus, ChannelProvider
from app.domain.models import ChannelAccount, ChannelContactIdentity, Customer, Shop
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.customer_repository import CustomerRepository
from app.schemas.conversation import ConversationRead


@pytest.mark.parametrize(
    "provider",
    [
        ChannelProvider.INSTAGRAM,
        ChannelProvider.WHATSAPP,
        ChannelProvider.TELEGRAM,
        ChannelProvider.BALE,
        ChannelProvider.RUBIKA,
    ],
)
def test_create_customer_from_channel_identity(db_session, provider) -> None:
    shop = Shop(name=f"{provider.value} shop", slug=f"{provider.value}-{uuid4()}")
    db_session.add(shop)
    db_session.flush()
    account = ChannelAccount(
        shop_id=shop.id,
        provider=provider,
        display_name=provider.value,
        external_account_id=str(uuid4()),
        status=ChannelAccountStatus.CONNECTED,
    )
    db_session.add(account)
    db_session.flush()

    customer = CustomerRepository(db_session).create_customer_from_channel_identity(
        shop_id=shop.id,
        provider=provider,
        channel_account_id=account.id,
        external_user_id="provider-user",
        display_name="Provider Customer",
    )

    if provider == ChannelProvider.INSTAGRAM:
        assert customer.instagram_user_id == "provider-user"
    else:
        assert customer.instagram_user_id is None
    assert customer.primary_channel_provider == provider
    assert customer.primary_external_user_id == "provider-user"
    assert CustomerRepository(db_session).get_customer_by_channel_identity(
        shop.id, provider, account.id, "provider-user"
    ) == customer


def test_identity_is_idempotent_and_multiple_providers_link_to_customer(db_session) -> None:
    shop = Shop(name="Multi", slug=f"multi-{uuid4()}")
    db_session.add(shop)
    db_session.flush()
    accounts = {}
    for provider in (ChannelProvider.WHATSAPP, ChannelProvider.TELEGRAM):
        account = ChannelAccount(
            shop_id=shop.id,
            provider=provider,
            display_name=provider.value,
            external_account_id=str(uuid4()),
        )
        db_session.add(account)
        db_session.flush()
        accounts[provider] = account
    repository = CustomerRepository(db_session)
    customer = repository.create_customer_from_channel_identity(
        shop_id=shop.id,
        provider=ChannelProvider.WHATSAPP,
        channel_account_id=accounts[ChannelProvider.WHATSAPP].id,
        external_user_id="wa-1",
    )
    first = repository.get_or_create_channel_contact_identity(
        shop_id=shop.id,
        customer_id=customer.id,
        provider=ChannelProvider.TELEGRAM,
        channel_account_id=accounts[ChannelProvider.TELEGRAM].id,
        external_user_id="tg-1",
    )
    second = repository.get_or_create_channel_contact_identity(
        shop_id=shop.id,
        customer_id=customer.id,
        provider=ChannelProvider.TELEGRAM,
        channel_account_id=accounts[ChannelProvider.TELEGRAM].id,
        external_user_id="tg-1",
    )

    assert first.id == second.id
    assert (
        db_session.query(ChannelContactIdentity)
        .filter(ChannelContactIdentity.customer_id == customer.id)
        .count()
        == 2
    )


def test_same_external_user_on_different_accounts_creates_distinct_customers(
    db_session,
) -> None:
    shop = Shop(name="Account scoped", slug=f"account-scoped-{uuid4()}")
    db_session.add(shop)
    db_session.flush()
    accounts = [
        ChannelAccount(
            shop_id=shop.id,
            provider=ChannelProvider.INSTAGRAM,
            display_name=f"Instagram {index}",
            external_account_id=str(uuid4()),
        )
        for index in range(2)
    ]
    db_session.add_all(accounts)
    db_session.flush()
    repository = CustomerRepository(db_session)

    customers = [
        repository.create_customer_from_channel_identity(
            shop_id=shop.id,
            provider=ChannelProvider.INSTAGRAM,
            channel_account_id=account.id,
            external_user_id="reused-user-id",
        )
        for account in accounts
    ]

    assert customers[0].id != customers[1].id


def test_create_conversation_without_instagram_account(db_session) -> None:
    shop = Shop(name="Telegram", slug=f"telegram-conversation-{uuid4()}")
    db_session.add(shop)
    db_session.flush()
    account = ChannelAccount(
        shop_id=shop.id,
        provider=ChannelProvider.TELEGRAM,
        display_name="Telegram",
        external_account_id=str(uuid4()),
    )
    customer = Customer(shop_id=shop.id, display_name="Telegram Customer")
    db_session.add_all([account, customer])
    db_session.flush()

    conversation = ConversationRepository(
        db_session
    ).get_or_create_conversation_by_channel(
        shop_id=shop.id,
        customer_id=customer.id,
        provider=ChannelProvider.TELEGRAM,
        channel_account_id=account.id,
        external_conversation_id="chat-1",
    )

    assert conversation.instagram_account_id is None
    assert conversation.channel_account_id == account.id
    assert conversation.external_conversation_id == "chat-1"


def test_channel_conversation_without_instagram_ids_serializes(db_session) -> None:
    shop = Shop(name="Serializable", slug=f"serializable-{uuid4()}")
    db_session.add(shop)
    db_session.flush()
    account = ChannelAccount(
        shop_id=shop.id,
        provider=ChannelProvider.WHATSAPP,
        display_name="WhatsApp",
        external_account_id=str(uuid4()),
    )
    customer = Customer(shop_id=shop.id, display_name="WhatsApp Customer")
    db_session.add_all([account, customer])
    db_session.flush()

    conversation = ConversationRepository(db_session).get_or_create_conversation_by_channel(
        shop_id=shop.id,
        customer_id=customer.id,
        provider=ChannelProvider.WHATSAPP,
        channel_account_id=account.id,
        external_conversation_id="wa-chat-1",
    )
    conversation.customer = customer

    serialized = ConversationRead.model_validate(conversation)

    assert serialized.instagram_account_id is None
    assert serialized.customer is not None
    assert serialized.customer.instagram_user_id is None
