import json
from decimal import Decimal
from uuid import UUID

from app.core.security import encrypt_secret
from app.domain.enums import (
    AgentWorkflowState,
    ChannelAccountStatus,
    ChannelProvider,
    ConfidenceSource,
    InstagramAccountStatus,
    MessageChannel,
    MessageDirection,
    MessageType,
    ProductStatus,
)
from app.domain.models import (
    ChannelAccount,
    Conversation,
    Customer,
    InstagramAccount,
    InstagramProductMap,
    Message,
    Product,
    ProductVariant,
)
from app.integrations.openai_client import MockOpenAIChatClient
from app.integrations.qdrant_client import MockQdrantClient
from app.services.conversation_orchestrator import ConversationOrchestrator
from app.services.product_semantic_search_service import ProductSemanticSearchService


def seed_order_flow_data(db_session, demo_shop) -> dict:
    account = InstagramAccount(
        shop_id=demo_shop.id,
        ig_user_id="17841400000000001",
        username="demo_shop",
        access_token_encrypted=encrypt_secret("token"),
        status=InstagramAccountStatus.CONNECTED,
    )
    db_session.add(account)
    db_session.flush()

    channel_account = ChannelAccount(
        shop_id=demo_shop.id,
        provider=ChannelProvider.INSTAGRAM,
        display_name=account.username,
        external_account_id=account.ig_user_id,
        bot_username=account.username,
        access_token_encrypted=account.access_token_encrypted,
        status=ChannelAccountStatus.CONNECTED,
        capabilities_json={"supports_text": True, "supports_images": True},
        settings_json={"legacy_instagram_account_id": str(account.id)},
    )
    db_session.add(channel_account)
    db_session.flush()

    customer = Customer(shop_id=demo_shop.id, instagram_user_id="cust-1")
    db_session.add(customer)
    db_session.flush()

    conversation = Conversation(
        shop_id=demo_shop.id,
        instagram_account_id=account.id,
        channel_account_id=channel_account.id,
        channel_provider=ChannelProvider.INSTAGRAM.value,
        external_conversation_id=customer.instagram_user_id,
        channel_conversation_id=customer.instagram_user_id,
        channel_customer_id=customer.instagram_user_id,
        customer_id=customer.id,
        workflow_state=AgentWorkflowState.IDLE,
    )
    db_session.add(conversation)
    db_session.flush()

    product = Product(
        shop_id=demo_shop.id,
        title="Classic Hoodie",
        description="Warm hoodie",
        status=ProductStatus.ACTIVE,
        base_price=Decimal("49.99"),
        currency="USD",
    )
    db_session.add(product)
    db_session.flush()

    variant = ProductVariant(
        product_id=product.id,
        color="Black",
        size="L",
        sku="HD-BLK-L",
        price=Decimal("49.99"),
        stock_quantity=10,
        reserved_quantity=0,
        is_active=True,
        normalized_color="black",
        normalized_size="L",
    )
    db_session.add(variant)
    db_session.flush()

    post_url = "https://www.instagram.com/p/ABC123/"
    mapping = InstagramProductMap(
        shop_id=demo_shop.id,
        instagram_account_id=account.id,
        instagram_media_id="media-abc",
        instagram_post_url=post_url,
        product_id=product.id,
        confidence_source=ConfidenceSource.MANUAL,
        is_active=True,
    )
    demo_shop.agent_settings = {
        **(demo_shop.agent_settings or {}),
        "preview_required_for_first_24h": False,
        "auto_send_confidence_threshold": 0.5,
    }
    db_session.add(mapping)
    db_session.commit()

    return {
        "account": account,
        "channel_account": channel_account,
        "customer": customer,
        "conversation": conversation,
        "product": product,
        "variant": variant,
        "mapping": mapping,
        "post_url": post_url,
    }


def build_orchestrator(
    db_session,
    *,
    llm_response: dict,
    qdrant_client: MockQdrantClient | None = None,
) -> ConversationOrchestrator:
    qdrant = qdrant_client or MockQdrantClient()
    chat_client = MockOpenAIChatClient(responses=[json.dumps(llm_response)])
    semantic = ProductSemanticSearchService(
        db_session,
        qdrant_client=qdrant,
        embedding_client=__import__(
            "app.integrations.openai_client", fromlist=["MockOpenAIEmbeddingClient"]
        ).MockOpenAIEmbeddingClient(),
    )
    return ConversationOrchestrator(
        db_session,
        chat_client=chat_client,
        qdrant_client=qdrant,
        semantic_search=semantic,
    )


def create_shared_post_message(
    db_session,
    conversation_id: UUID,
    post_url: str,
    text: str,
    *,
    instagram_media_id: str = "media-abc",
) -> Message:
    conversation = db_session.get(Conversation, conversation_id)
    message = Message(
        shop_id=conversation.shop_id,
        conversation_id=conversation_id,
        customer_id=conversation.customer_id,
        channel_provider=ChannelProvider.INSTAGRAM,
        channel_account_id=conversation.channel_account_id,
        direction=MessageDirection.INBOUND,
        channel=MessageChannel.INSTAGRAM,
        message_type=MessageType.SHARED_POST,
        text=text,
        raw_payload={
            "_meta": {"shared_post_url": post_url},
            "message": {"attachments": [{"payload": {"ig_post_media_id": instagram_media_id}}]},
        },
    )
    db_session.add(message)
    db_session.commit()
    db_session.refresh(message)
    return message


def create_text_message(
    db_session, conversation_id: UUID, text: str, *, instagram_message_id: str | None = None
) -> Message:
    conversation = db_session.get(Conversation, conversation_id)
    message = Message(
        shop_id=conversation.shop_id,
        conversation_id=conversation_id,
        customer_id=conversation.customer_id,
        channel_provider=ChannelProvider.INSTAGRAM,
        channel_account_id=conversation.channel_account_id,
        direction=MessageDirection.INBOUND,
        channel=MessageChannel.INSTAGRAM,
        instagram_message_id=instagram_message_id,
        message_type=MessageType.TEXT,
        text=text,
        raw_payload={},
    )
    db_session.add(message)
    db_session.commit()
    db_session.refresh(message)
    return message
