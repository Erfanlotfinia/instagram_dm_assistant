from decimal import Decimal
from app.domain.enums import ProductStatus
from app.domain.models import Product, ProductVariant
from app.integrations.openai_client import MockOpenAIEmbeddingClient
from app.integrations.qdrant_client import MockQdrantClient
from app.schemas.agent import SemanticSearchRequest
from app.services.auth_service import AuthService
from app.services.product_semantic_search_service import ProductSemanticSearchService


def test_semantic_search_uses_mock_qdrant(db_session, demo_shop, admin_user) -> None:
    product = Product(
        shop_id=demo_shop.id,
        title="Red Summer Dress",
        description="Light dress",
        status=ProductStatus.ACTIVE,
        base_price=Decimal("29.99"),
        currency="USD",
    )
    db_session.add(product)
    db_session.flush()
    variant = ProductVariant(
        product_id=product.id,
        color="Red",
        size="M",
        sku="DR-RED-M",
        price=Decimal("29.99"),
        stock_quantity=5,
    )
    db_session.add(variant)
    db_session.commit()

    qdrant = MockQdrantClient()
    embeddings = MockOpenAIEmbeddingClient()
    service = ProductSemanticSearchService(
        db_session,
        qdrant_client=qdrant,
        embedding_client=embeddings,
    )
    service.index_product(product, [variant], caption="summer dress")

    response = service.search_for_shop(
        demo_shop.id,
        SemanticSearchRequest(query="summer dress red"),
        admin_user,
    )

    assert len(response.hits) == 1
    assert response.hits[0].product_id == product.id
    assert response.hits[0].title == "Red Summer Dress"
