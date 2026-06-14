from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import OrderStatus
from app.domain.models import Order, Product, ProductVariant
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.variant_repository import VariantRepository
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService
from app.services.social_admin.catalog_query_planner import CatalogQueryPlanner
from app.services.social_admin.context_graph import ConversationContextService


@dataclass
class HandlerContext:
    shop_id: UUID
    conversation_id: UUID
    message_id: UUID | None = None
    message_text: str = ""
    provider: str = "instagram"
    raw_provider_payload: dict[str, Any] = field(default_factory=dict)
    active_order: Order | None = None
    referenced_product_id: UUID | None = None
    referenced_variant_id: UUID | None = None
    is_simulation: bool = False


@dataclass
class HandlerDecision:
    can_handle: bool
    confidence: float
    reasons: list[str] = field(default_factory=list)


@dataclass
class HandlerResult:
    status: str
    response_text: str | None = None
    response_template_key: str | None = None
    actions: list[dict[str, Any]] = field(default_factory=list)
    suggested_replies: list[str] = field(default_factory=list)
    order_action: dict[str, Any] | None = None
    catalog_action: dict[str, Any] | None = None
    handoff_reason: str | None = None
    confidence: float = 0.0
    audit_metadata: dict[str, Any] = field(default_factory=dict)


class BaseAutomationHandler:
    scenario_code = "GENERIC"
    requires_llm = False
    handler_name: str = "BaseAutomationHandler"

    def can_handle(self, context: HandlerContext) -> HandlerDecision:
        return HandlerDecision(True, 0.75, [self.scenario_code])

    def handle(self, context: HandlerContext) -> HandlerResult:
        return HandlerResult(
            "handled",
            response_text="Handled deterministically.",
            confidence=0.75,
            audit_metadata={"handler": self.handler_name, "llm_used": False},
        )


class _ServiceBackedHandler(BaseAutomationHandler):
    def __init__(
        self,
        db: Session,
        context_service: ConversationContextService,
        *,
        settings: Any = None,
    ) -> None:
        self.db = db
        self.context_service = context_service
        self.products = ProductRepository(db)
        self.variants = VariantRepository(db)
        self.orders = OrderRepository(db)
        self.order_service = OrderService(db, settings=settings)
        self.payment_service = PaymentService(db, settings=settings)
        self.catalog_planner = CatalogQueryPlanner()

    def _product(self, product_id: UUID | str | None, shop_id: UUID) -> Product | None:
        if product_id is None:
            return None
        try:
            pid = product_id if isinstance(product_id, UUID) else UUID(str(product_id))
        except ValueError:
            return None
        product = self.products.get_by_id(pid)
        if product is None or product.shop_id != shop_id:
            return None
        return product

    def _resolve_product_from_context(self, context: HandlerContext) -> Product | None:
        if context.referenced_product_id:
            return self._product(context.referenced_product_id, context.shop_id)
        ref = self.context_service.resolve_reference(
            {"text": context.message_text},
            str(context.conversation_id),
            shop_id=str(context.shop_id),
        )
        if ref.selected_product_id:
            return self._product(ref.selected_product_id, context.shop_id)
        active = self.context_service.get_active_product_context(
            str(context.conversation_id), shop_id=str(context.shop_id)
        )
        if active and active.selected_product_id:
            return self._product(active.selected_product_id, context.shop_id)
        return None

    def _variant_stock(self, product: Product) -> tuple[int, Decimal | None]:
        variants = self.db.scalars(
            select(ProductVariant).where(
                ProductVariant.product_id == product.id,
                ProductVariant.is_active.is_(True),
            )
        ).all()
        total = sum(v.stock_quantity or 0 for v in variants)
        price = variants[0].price if variants else product.base_price
        return total, price


class AskPriceReferencedProductHandler(_ServiceBackedHandler):
    scenario_code = "ASK_PRICE_REFERENCED_PRODUCT"
    handler_name = "AskPriceReferencedProductHandler"

    def handle(self, context: HandlerContext) -> HandlerResult:
        product = self._resolve_product_from_context(context)
        if product is None:
            return HandlerResult(
                "needs_clarification",
                response_text="Which product are you asking about? Send a link, photo, or product name.",
                confidence=0.5,
                audit_metadata={"handler": self.handler_name, "llm_used": False},
            )
        _, price = self._variant_stock(product)
        amount = price or product.base_price
        return HandlerResult(
            "handled",
            response_text=f"{product.title} is {amount} {product.currency}.",
            confidence=0.9,
            audit_metadata={
                "handler": self.handler_name,
                "llm_used": False,
                "product_id": str(product.id),
            },
        )


class AskStockReferencedProductHandler(_ServiceBackedHandler):
    scenario_code = "ASK_STOCK_REFERENCED_PRODUCT"
    handler_name = "AskStockReferencedProductHandler"

    def handle(self, context: HandlerContext) -> HandlerResult:
        product = self._resolve_product_from_context(context)
        if product is None:
            return HandlerResult(
                "needs_clarification",
                response_text="Which product availability should I check?",
                confidence=0.5,
                audit_metadata={"handler": self.handler_name, "llm_used": False},
            )
        stock, _ = self._variant_stock(product)
        text = (
            f"{product.title} is in stock ({stock} available)."
            if stock > 0
            else f"{product.title} is currently unavailable."
        )
        return HandlerResult(
            "handled",
            response_text=text,
            confidence=0.9,
            audit_metadata={
                "handler": self.handler_name,
                "llm_used": False,
                "product_id": str(product.id),
                "stock": stock,
            },
        )


class AskDetailsReferencedProductHandler(_ServiceBackedHandler):
    scenario_code = "ASK_DETAILS_REFERENCED_PRODUCT"
    handler_name = "AskDetailsReferencedProductHandler"

    def handle(self, context: HandlerContext) -> HandlerResult:
        product = self._resolve_product_from_context(context)
        if product is None:
            return HandlerResult(
                "needs_clarification",
                response_text="Which product details do you need?",
                confidence=0.5,
                audit_metadata={"handler": self.handler_name, "llm_used": False},
            )
        stock, price = self._variant_stock(product)
        desc = product.description or "No description available."
        return HandlerResult(
            "handled",
            response_text=(
                f"{product.title}: {desc[:200]} Price: {price or product.base_price} "
                f"{product.currency}. Stock: {stock}."
            ),
            confidence=0.88,
            audit_metadata={"handler": self.handler_name, "llm_used": False},
        )


class BuyReferencedProductHandler(_ServiceBackedHandler):
    scenario_code = "BUY_REFERENCED_PRODUCT"
    handler_name = "BuyReferencedProductHandler"

    def handle(self, context: HandlerContext) -> HandlerResult:
        product = self._resolve_product_from_context(context)
        if product is None:
            return HandlerResult(
                "needs_clarification",
                response_text="Which product would you like to order?",
                confidence=0.5,
                audit_metadata={"handler": self.handler_name, "llm_used": False},
            )
        if context.is_simulation:
            return HandlerResult(
                "handled",
                response_text=f"Starting order for {product.title}. Please share size/color if needed.",
                confidence=0.86,
                order_action={"action": "start_order", "product_id": str(product.id)},
                audit_metadata={"handler": self.handler_name, "llm_used": False},
            )
        return HandlerResult(
            "handled",
            response_text=f"Let's order {product.title}. Please confirm size, color, and quantity.",
            confidence=0.86,
            order_action={"action": "start_order", "product_id": str(product.id)},
            audit_metadata={"handler": self.handler_name, "llm_used": False},
        )


class SelectFromProductListHandler(_ServiceBackedHandler):
    scenario_code = "PRODUCT_LIST_SELECTION"
    handler_name = "SelectFromProductListHandler"

    def handle(self, context: HandlerContext) -> HandlerResult:
        ref = self.context_service.resolve_reference(
            {"text": context.message_text},
            str(context.conversation_id),
            shop_id=str(context.shop_id),
        )
        if ref.selected_product_id:
            product = self._product(ref.selected_product_id, context.shop_id)
            if product:
                return HandlerResult(
                    "handled",
                    response_text=f"Selected: {product.title}. Would you like price, stock, or to buy?",
                    confidence=ref.confidence,
                    audit_metadata={
                        "handler": self.handler_name,
                        "llm_used": False,
                        "product_id": str(product.id),
                    },
                )
        return HandlerResult(
            "needs_clarification",
            response_text=ref.clarification_question or "Which item from the list do you mean?",
            confidence=0.5,
            audit_metadata={"handler": self.handler_name, "llm_used": False},
        )


class AmbiguousReferenceClarificationHandler(BaseAutomationHandler):
    scenario_code = "AMBIGUOUS_REFERENCE"
    handler_name = "AmbiguousReferenceClarificationHandler"

    def handle(self, context: HandlerContext) -> HandlerResult:
        return HandlerResult(
            "needs_clarification",
            response_text="I'm not sure which product you mean. Please send the link, photo, or list number.",
            confidence=0.55,
            audit_metadata={"handler": self.handler_name, "llm_used": False},
        )


class HumanRequestHandler(BaseAutomationHandler):
    scenario_code = "HUMAN_REQUEST"
    handler_name = "HumanRequestHandler"

    def handle(self, context: HandlerContext) -> HandlerResult:
        return HandlerResult(
            "needs_human",
            handoff_reason="Customer requested human operator",
            confidence=0.98,
            audit_metadata={"handler": self.handler_name, "llm_used": False},
        )


class ComplaintHandler(BaseAutomationHandler):
    scenario_code = "COMPLAINT"
    handler_name = "ComplaintHandler"

    def handle(self, context: HandlerContext) -> HandlerResult:
        return HandlerResult(
            "needs_human",
            handoff_reason="Complaint requires human review",
            confidence=0.85,
            audit_metadata={"handler": self.handler_name, "llm_used": False},
        )


class SpamAbuseHandler(BaseAutomationHandler):
    scenario_code = "SPAM_ABUSE"
    handler_name = "SpamAbuseHandler"

    def handle(self, context: HandlerContext) -> HandlerResult:
        return HandlerResult(
            "needs_human",
            handoff_reason="Spam or abuse signal detected",
            confidence=0.85,
            audit_metadata={"handler": self.handler_name, "llm_used": False},
        )


class PaymentMethodsHandler(BaseAutomationHandler):
    scenario_code = "PAYMENT_METHODS"
    handler_name = "PaymentMethodsHandler"

    def handle(self, context: HandlerContext) -> HandlerResult:
        return HandlerResult(
            "handled",
            response_text="We accept online payment link, card transfer, and manual payment with receipt.",
            confidence=0.9,
            audit_metadata={"handler": self.handler_name, "llm_used": False},
        )


class SendPaymentLinkHandler(_ServiceBackedHandler):
    scenario_code = "PAYMENT_LINK"
    handler_name = "SendPaymentLinkHandler"

    def handle(self, context: HandlerContext) -> HandlerResult:
        order = context.active_order or self.orders.get_active_for_conversation(
            context.conversation_id
        )
        if order is None:
            return HandlerResult(
                "needs_clarification",
                response_text="Please confirm your order first before requesting a payment link.",
                confidence=0.6,
                audit_metadata={"handler": self.handler_name, "llm_used": False},
            )
        if order.status not in {
            OrderStatus.READY_FOR_CONFIRMATION,
            OrderStatus.PAYMENT_PENDING,
            OrderStatus.RESERVED,
        }:
            return HandlerResult(
                "needs_clarification",
                response_text="Your order is not ready for payment yet. Please complete order details first.",
                confidence=0.7,
                audit_metadata={"handler": self.handler_name, "llm_used": False},
            )
        return HandlerResult(
            "handled",
            response_text="I can send a payment link after you confirm the order summary.",
            confidence=0.88,
            audit_metadata={"handler": self.handler_name, "llm_used": False},
        )


class ManualPaymentReceiptHandler(BaseAutomationHandler):
    scenario_code = "MANUAL_PAYMENT"
    handler_name = "ManualPaymentReceiptHandler"

    def handle(self, context: HandlerContext) -> HandlerResult:
        return HandlerResult(
            "handled",
            response_text="Please send your payment receipt image. An operator will verify it.",
            confidence=0.86,
            audit_metadata={"handler": self.handler_name, "llm_used": False},
        )


class OrderSummaryHandler(_ServiceBackedHandler):
    scenario_code = "ORDER_SUMMARY"
    handler_name = "OrderSummaryHandler"

    def handle(self, context: HandlerContext) -> HandlerResult:
        order = context.active_order or self.orders.get_active_for_conversation(
            context.conversation_id
        )
        if order is None:
            return HandlerResult(
                "needs_clarification",
                response_text="There is no active order to summarize.",
                confidence=0.5,
                audit_metadata={"handler": self.handler_name, "llm_used": False},
            )
        return HandlerResult(
            "handled",
            response_text=f"Order #{order.id}: status {order.status.value}, total {order.total_amount}.",
            confidence=0.92,
            audit_metadata={"handler": self.handler_name, "llm_used": False},
        )


class ConfirmOrderHandler(_ServiceBackedHandler):
    scenario_code = "ORDER_CONFIRM"
    handler_name = "ConfirmOrderHandler"

    def handle(self, context: HandlerContext) -> HandlerResult:
        order = context.active_order or self.orders.get_active_for_conversation(
            context.conversation_id
        )
        if order is None:
            return HandlerResult(
                "needs_clarification",
                response_text="No active order to confirm.",
                confidence=0.5,
                audit_metadata={"handler": self.handler_name, "llm_used": False},
            )
        return HandlerResult(
            "handled",
            response_text="Please review the order summary and confirm to proceed to payment.",
            confidence=0.9,
            order_action={"action": "confirm_order", "order_id": str(order.id)},
            audit_metadata={"handler": self.handler_name, "llm_used": False},
        )


class CancelOrderHandler(_ServiceBackedHandler):
    scenario_code = "ORDER_CANCEL"
    handler_name = "CancelOrderHandler"

    def handle(self, context: HandlerContext) -> HandlerResult:
        order = context.active_order or self.orders.get_active_for_conversation(
            context.conversation_id
        )
        if order is None:
            return HandlerResult(
                "handled",
                response_text="No active order to cancel.",
                confidence=0.7,
                audit_metadata={"handler": self.handler_name, "llm_used": False},
            )
        if not context.is_simulation:
            self.order_service.cancel_active_for_conversation(
                context.conversation_id, reason="customer_cancel_request"
            )
        return HandlerResult(
            "handled",
            response_text="Your order has been cancelled.",
            confidence=0.92,
            order_action={"action": "cancel_order", "order_id": str(order.id)},
            audit_metadata={"handler": self.handler_name, "llm_used": False},
        )


class CatalogListHandler(_ServiceBackedHandler):
    scenario_code = "CATALOG_LIST"
    handler_name = "CatalogListHandler"

    def __init__(
        self,
        db: Session,
        context_service: ConversationContextService,
        *,
        settings: Any = None,
        list_label: str = "products",
    ) -> None:
        super().__init__(db, context_service, settings=settings)
        self.list_label = list_label
        self.handler_name = f"List{list_label}Handler"

    def handle(self, context: HandlerContext) -> HandlerResult:
        plan = self.catalog_planner.plan(context.message_text)
        products = self.db.scalars(
            select(Product).where(Product.shop_id == context.shop_id).limit(5)
        ).all()
        if not products:
            return HandlerResult(
                "handled",
                response_text="No matching products found in the catalog.",
                confidence=0.7,
                audit_metadata={"handler": self.handler_name, "llm_used": False},
            )
        lines = [f"{i + 1}. {p.title}" for i, p in enumerate(products)]
        product_ids = [str(p.id) for p in products]
        self.context_service.add_context_item(
            shop_id=str(context.shop_id),
            conversation_id=str(context.conversation_id),
            provider=context.provider,
            item_type="product_list",
            candidate_product_ids_json=product_ids,
            title=f"{self.list_label} results",
        )
        return HandlerResult(
            "handled",
            response_text="Here are some options:\n" + "\n".join(lines),
            confidence=plan.confidence,
            catalog_action={"product_ids": product_ids, "plan": plan.query_type},
            audit_metadata={"handler": self.handler_name, "llm_used": False},
        )


def _simple_handler(name: str, response: str, status: str = "handled") -> BaseAutomationHandler:
    handler = type(
        name,
        (BaseAutomationHandler,),
        {
            "handler_name": name,
            "handle": lambda self, context: HandlerResult(
                status,
                response_text=response,
                confidence=0.8,
                audit_metadata={"handler": name, "llm_used": False},
            ),
        },
    )
    return handler()


HANDLER_NAMES = [
    "AddItemHandler",
    "RemoveItemHandler",
    "ChangeQuantityHandler",
    "ChangeAttributeHandler",
    "EditOrderHandler",
    "StartOrderHandler",
    "PaymentStatusHandler",
    "PaymentFailedHandler",
    "SuspiciousPaymentHandoffHandler",
    "ShippingCostHandler",
    "ShippingMethodsHandler",
    "DeliveryTimeHandler",
    "AddressCaptureHandler",
    "AddressChangeHandler",
    "TrackingCodeHandler",
    "OrderStatusHandler",
    "DeliveryComplaintHandler",
    "PolicyQuestionHandler",
    "ReturnRequestHandler",
    "ExchangeRequestHandler",
    "OffTopicHandler",
    "CampaignQuestionHandler",
    "NewArrivalsHandler",
    "DiscountQuestionHandler",
    "CatalogExportHandler",
    "AdminReplySuggestionHandler",
    "AdminCaptionDraftHandler",
    "AdminStoryDraftHandler",
    "ConversationSummaryHandler",
    "FAQMiningHandler",
    "ProductSearchByPriceRangeHandler",
    "SimilarProductsHandler",
    "CompareProductsHandler",
    "BestSellersHandler",
    "AvailableProductsOnlyHandler",
    "ProductSearchByAttributesHandler",
]


class AutomationHandlerRegistry:
    def __init__(
        self,
        db: Session | None = None,
        context_service: ConversationContextService | None = None,
        *,
        settings: Any = None,
    ) -> None:
        self.db = db
        ctx = context_service or ConversationContextService(db)
        self.handlers: dict[str, BaseAutomationHandler] = {}
        if db is not None:
            self.handlers["AskPriceReferencedProductHandler"] = AskPriceReferencedProductHandler(
                db, ctx, settings=settings
            )
            self.handlers["AskStockReferencedProductHandler"] = AskStockReferencedProductHandler(
                db, ctx, settings=settings
            )
            self.handlers["AskDetailsReferencedProductHandler"] = (
                AskDetailsReferencedProductHandler(db, ctx, settings=settings)
            )
            self.handlers["BuyReferencedProductHandler"] = BuyReferencedProductHandler(
                db, ctx, settings=settings
            )
            self.handlers["SelectFromProductListHandler"] = SelectFromProductListHandler(
                db, ctx, settings=settings
            )
            self.handlers["SendPaymentLinkHandler"] = SendPaymentLinkHandler(
                db, ctx, settings=settings
            )
            self.handlers["OrderSummaryHandler"] = OrderSummaryHandler(db, ctx, settings=settings)
            self.handlers["ConfirmOrderHandler"] = ConfirmOrderHandler(db, ctx, settings=settings)
            self.handlers["CancelOrderHandler"] = CancelOrderHandler(db, ctx, settings=settings)
            self.handlers["ListProductsByCategoryHandler"] = CatalogListHandler(
                db, ctx, settings=settings, list_label="ProductsByCategory"
            )
            self.handlers["ListProductsByBrandHandler"] = CatalogListHandler(
                db, ctx, settings=settings, list_label="ProductsByBrand"
            )
            self.handlers["ProductSearchByAttributesHandler"] = CatalogListHandler(
                db, ctx, settings=settings, list_label="ByAttributes"
            )
            self.handlers["ProductSearchByPriceRangeHandler"] = CatalogListHandler(
                db, ctx, settings=settings, list_label="ByPriceRange"
            )
            self.handlers["SimilarProductsHandler"] = CatalogListHandler(
                db, ctx, settings=settings, list_label="Similar"
            )
            self.handlers["CompareProductsHandler"] = CatalogListHandler(
                db, ctx, settings=settings, list_label="Compare"
            )
            self.handlers["BestSellersHandler"] = CatalogListHandler(
                db, ctx, settings=settings, list_label="BestSellers"
            )
            self.handlers["AvailableProductsOnlyHandler"] = CatalogListHandler(
                db, ctx, settings=settings, list_label="Available"
            )
        self.handlers["AmbiguousReferenceClarificationHandler"] = AmbiguousReferenceClarificationHandler()
        self.handlers["HumanRequestHandler"] = HumanRequestHandler()
        self.handlers["ComplaintHandler"] = ComplaintHandler()
        self.handlers["SpamAbuseHandler"] = SpamAbuseHandler()
        self.handlers["PaymentMethodsHandler"] = PaymentMethodsHandler()
        self.handlers["ManualPaymentReceiptHandler"] = ManualPaymentReceiptHandler()
        simple_responses = {
            "AddItemHandler": "Which product should I add to your order?",
            "RemoveItemHandler": "Which item should I remove from your order?",
            "ChangeQuantityHandler": "What quantity would you like?",
            "ChangeAttributeHandler": "Which attribute should I change (size, color)?",
            "EditOrderHandler": "What would you like to edit in your order?",
            "StartOrderHandler": "Which product would you like to order?",
            "PaymentStatusHandler": "I'll check your payment status.",
            "PaymentFailedHandler": "Payment failed. You can retry or contact support.",
            "SuspiciousPaymentHandoffHandler": "This payment needs operator review.",
            "ShippingCostHandler": "Shipping cost depends on your city and method.",
            "ShippingMethodsHandler": "We offer standard and express shipping.",
            "DeliveryTimeHandler": "Delivery time is typically 2-5 business days.",
            "AddressCaptureHandler": "Please send your full address with phone number.",
            "AddressChangeHandler": "Send the updated delivery address.",
            "TrackingCodeHandler": "I'll share your tracking code when available.",
            "OrderStatusHandler": "I'll check your order status.",
            "DeliveryComplaintHandler": "Sorry about the delivery issue. An operator will help.",
            "PolicyQuestionHandler": "Our shop policies are available on the website.",
            "ReturnRequestHandler": "Please describe the return reason and order number.",
            "ExchangeRequestHandler": "Please describe what you'd like to exchange.",
            "OffTopicHandler": "I can help with products, orders, and shop support.",
            "CampaignQuestionHandler": "Current campaigns are listed on our catalog.",
            "NewArrivalsHandler": "Here are our newest arrivals from the catalog.",
            "DiscountQuestionHandler": "Active discounts are shown on each product in the catalog.",
            "CatalogExportHandler": "Catalog export is available from the admin panel.",
            "AdminReplySuggestionHandler": "Reply suggestion is available in admin tasks.",
            "AdminCaptionDraftHandler": "Caption draft requires admin approval before publishing.",
            "AdminStoryDraftHandler": "Story draft requires admin approval before publishing.",
            "ConversationSummaryHandler": "Conversation summary is available in admin tasks.",
            "FAQMiningHandler": "FAQ mining is available in admin tasks.",
        }
        for name, response in simple_responses.items():
            if name not in self.handlers:
                inst = _simple_handler(name, response)
                if name == "SuspiciousPaymentHandoffHandler":
                    inst = _simple_handler(name, response, status="needs_human")
                    inst.handler_name = name
                self.handlers[name] = inst

    def get(self, name: str) -> BaseAutomationHandler | None:
        return self.handlers.get(name)

    def dispatch(self, name: str, context: HandlerContext | dict[str, Any]) -> HandlerResult:
        if isinstance(context, dict):
            shop_raw = context.get("shop_id") or "00000000-0000-0000-0000-000000000001"
            conv_raw = context.get("conversation_id") or "00000000-0000-0000-0000-000000000002"
            ctx = HandlerContext(
                shop_id=UUID(str(shop_raw)),
                conversation_id=UUID(str(conv_raw)),
                message_text=context.get("message_text", ""),
                provider=context.get("provider", "instagram"),
                is_simulation=context.get("is_simulation", False),
            )
        else:
            ctx = context
        handler = self.get(name)
        if not handler:
            return HandlerResult(
                "needs_human",
                handoff_reason="No registered handler",
                confidence=0,
                audit_metadata={"handler": name, "llm_used": False},
            )
        decision = handler.can_handle(ctx)
        if not decision.can_handle or decision.confidence < 0.5:
            return HandlerResult(
                "needs_clarification",
                response_text="Can you clarify?",
                confidence=decision.confidence,
                audit_metadata={"handler": name, "llm_used": False},
            )
        return handler.handle(ctx)
