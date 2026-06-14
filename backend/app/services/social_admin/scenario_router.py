from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.services.social_admin.catalog_query_planner import CatalogQueryPlanner
from app.services.social_admin.referenced_content_resolver import ReferencedContentResolver


@dataclass
class ScenarioDecision:
    scenario_code: str
    confidence: float
    handler: str
    requires_llm: bool = False
    requires_handoff: bool = False
    reasons: list[str] = field(default_factory=list)


class ScenarioRouter:
    def __init__(
        self,
        context_service: Any | None = None,
        catalog_planner: CatalogQueryPlanner | None = None,
    ) -> None:
        self.context_service = context_service
        self.catalog_planner = catalog_planner or CatalogQueryPlanner()
        self.referenced_resolver = (
            ReferencedContentResolver(context_service) if context_service else None
        )

    def route(
        self,
        message: Any,
        conversation_context: Any = None,
        customer_profile: Any = None,
        active_order: Any = None,
        channel_capabilities: Any = None,
        shop_settings: Any = None,
        shop_id: str | None = None,
        conversation_id: str | None = None,
        raw_provider_payload: dict[str, Any] | None = None,
    ) -> ScenarioDecision:
        text = (
            getattr(message, "text", None)
            or (message.get("text") if isinstance(message, dict) else "")
            or ""
        )
        low = text.lower()
        payload = getattr(message, "payload", None) or (
            message.get("payload") if isinstance(message, dict) else None
        )
        button_id = getattr(message, "button_id", None) or (
            message.get("button_id") if isinstance(message, dict) else None
        )

        if payload or button_id:
            return ScenarioDecision(
                "BUTTON_CALLBACK",
                0.99,
                "SelectFromProductListHandler",
                reasons=["button/callback payload"],
            )

        if low.startswith("/"):
            return ScenarioDecision(
                "EXPLICIT_COMMAND",
                0.96,
                "CatalogExportHandler",
                reasons=["explicit command"],
            )

        if active_order:
            if any(w in low for w in ["cancel", "لغو", "کنسل"]):
                return ScenarioDecision(
                    "ORDER_CANCEL",
                    0.92,
                    "CancelOrderHandler",
                    reasons=["active order cancellation"],
                )
            if any(w in low for w in ["summary", "خلاصه"]):
                return ScenarioDecision(
                    "ORDER_SUMMARY",
                    0.92,
                    "OrderSummaryHandler",
                    reasons=["active order summary"],
                )
            if any(w in low for w in ["confirm", "تایید", "اوکی"]):
                return ScenarioDecision(
                    "ORDER_CONFIRM",
                    0.9,
                    "ConfirmOrderHandler",
                    reasons=["active order confirmation"],
                )
            if any(w in low for w in ["add", "اضافه"]):
                return ScenarioDecision(
                    "ORDER_ADD_ITEM",
                    0.88,
                    "AddItemHandler",
                    reasons=["active order add item"],
                )
            if any(w in low for w in ["remove", "حذف"]):
                return ScenarioDecision(
                    "ORDER_REMOVE_ITEM",
                    0.88,
                    "RemoveItemHandler",
                    reasons=["active order remove item"],
                )

        conv_id = conversation_id or (
            conversation_context.get("conversation_id")
            if isinstance(conversation_context, dict)
            else getattr(conversation_context, "conversation_id", None)
        )
        if self.referenced_resolver and conv_id and self._has_reference_signal(low, raw_provider_payload):
            ref = self.referenced_resolver.resolve(
                message, raw_provider_payload, str(conv_id)
            )
            if ref.needs_clarification and ref.confidence < 0.5:
                return ScenarioDecision(
                    "AMBIGUOUS_REFERENCE",
                    0.55,
                    "AmbiguousReferenceClarificationHandler",
                    reasons=["ambiguous reference"],
                )
            if ref.selected_product_id or ref.external_url or ref.external_reference_id:
                if any(w in low for w in ["price", "قیمت", "چند", "چنده"]):
                    return ScenarioDecision(
                        "ASK_PRICE_REFERENCED_PRODUCT",
                        0.9,
                        "AskPriceReferencedProductHandler",
                        reasons=["referenced product price"],
                    )
                if any(w in low for w in ["stock", "available", "موجود", "داری"]):
                    return ScenarioDecision(
                        "ASK_STOCK_REFERENCED_PRODUCT",
                        0.9,
                        "AskStockReferencedProductHandler",
                        reasons=["referenced product stock"],
                    )
                if any(w in low for w in ["detail", "جزئیات", "اطلاعات"]):
                    return ScenarioDecision(
                        "ASK_DETAILS_REFERENCED_PRODUCT",
                        0.88,
                        "AskDetailsReferencedProductHandler",
                        reasons=["referenced product details"],
                    )
                if any(w in low for w in ["buy", "میخوام", "می‌خوام", "بده", "بخرم"]):
                    return ScenarioDecision(
                        "BUY_REFERENCED_PRODUCT",
                        0.88,
                        "BuyReferencedProductHandler",
                        reasons=["referenced product buy"],
                    )
            if ref.selected_context_item_id and any(
                w in low for w in ["second", "دوم", "دومی", "اول", "first", "one"]
            ):
                return ScenarioDecision(
                    "PRODUCT_LIST_SELECTION",
                    0.92,
                    "SelectFromProductListHandler",
                    reasons=["product list selection"],
                )

        if any(w in low for w in ["human", "admin", "اپراتور", "مدیر"]):
            return ScenarioDecision(
                "HUMAN_REQUEST",
                0.98,
                "HumanRequestHandler",
                requires_handoff=True,
                reasons=["human requested"],
            )
        if any(w in low for w in ["complaint", "angry", "ناراضی", "شکایت"]):
            return ScenarioDecision(
                "COMPLAINT",
                0.8,
                "ComplaintHandler",
                requires_handoff=True,
                reasons=["complaint risk"],
            )
        if any(w in low for w in ["spam", "abuse", "مسدود"]):
            return ScenarioDecision(
                "SPAM_ABUSE",
                0.85,
                "SpamAbuseHandler",
                requires_handoff=True,
                reasons=["spam/abuse signal"],
            )

        if any(w in low for w in ["payment method", "روش پرداخت", "چطور پرداخت"]):
            return ScenarioDecision(
                "PAYMENT_METHODS",
                0.9,
                "PaymentMethodsHandler",
                reasons=["payment methods question"],
            )
        if any(w in low for w in ["payment link", "لینک پرداخت"]):
            return ScenarioDecision(
                "PAYMENT_LINK",
                0.88,
                "SendPaymentLinkHandler",
                reasons=["payment link request"],
            )
        if any(w in low for w in ["paid", "پرداخت کردم", "واریز"]):
            return ScenarioDecision(
                "MANUAL_PAYMENT",
                0.86,
                "ManualPaymentReceiptHandler",
                reasons=["manual payment claim"],
            )
        if any(w in low for w in ["shipping", "ارسال", "پست", "delivery", "تحویل"]):
            if any(w in low for w in ["cost", "هزینه", "چقدر"]):
                return ScenarioDecision(
                    "SHIPPING_COST",
                    0.88,
                    "ShippingCostHandler",
                    reasons=["shipping cost"],
                )
            if any(w in low for w in ["track", "پیگیری", "کد"]):
                return ScenarioDecision(
                    "TRACKING_CODE",
                    0.86,
                    "TrackingCodeHandler",
                    reasons=["tracking code"],
                )
            return ScenarioDecision(
                "SHIPPING_METHODS",
                0.84,
                "ShippingMethodsHandler",
                reasons=["shipping question"],
            )
        if any(w in low for w in ["return", "مرجوع", "پس گرفتن"]):
            return ScenarioDecision(
                "RETURN_REQUEST",
                0.86,
                "ReturnRequestHandler",
                reasons=["return request"],
            )
        if any(w in low for w in ["exchange", "تعویض"]):
            return ScenarioDecision(
                "EXCHANGE_REQUEST",
                0.86,
                "ExchangeRequestHandler",
                reasons=["exchange request"],
            )
        if any(w in low for w in ["policy", "قوانین", "شرایط"]):
            return ScenarioDecision(
                "POLICY_QUESTION",
                0.84,
                "PolicyQuestionHandler",
                reasons=["policy question"],
            )

        if any(w in low for w in ["price", "قیمت", "چند", "چنده"]):
            return ScenarioDecision(
                "ASK_PRICE_REFERENCED_PRODUCT",
                0.88,
                "AskPriceReferencedProductHandler",
                reasons=["deterministic price keyword"],
            )
        if any(w in low for w in ["stock", "available", "موجود", "داری"]):
            return ScenarioDecision(
                "ASK_STOCK_REFERENCED_PRODUCT",
                0.88,
                "AskStockReferencedProductHandler",
                reasons=["deterministic stock keyword"],
            )
        if any(w in low for w in ["buy", "میخوام", "می‌خوام", "بخرم", "سفارش"]) or (
            "بده" in low and "نشون" not in low
        ):
            return ScenarioDecision(
                "BUY_REFERENCED_PRODUCT",
                0.86,
                "BuyReferencedProductHandler",
                reasons=["deterministic buy keyword"],
            )
        if any(w in low for w in ["best seller", "پرفروش"]):
            return ScenarioDecision(
                "BEST_SELLERS",
                0.88,
                "BestSellersHandler",
                reasons=["best sellers"],
            )

        plan = self.catalog_planner.plan(text, shop_id=shop_id)
        if plan.confidence >= 0.8 and not plan.needs_clarification:
            handler = self._handler_for_catalog_plan(plan)
            return ScenarioDecision(
                f"CATALOG_{plan.query_type.upper()}",
                plan.confidence,
                handler,
                reasons=["catalog query planner"],
            )

        if any(w in low for w in ["similar", "مشابه"]):
            return ScenarioDecision(
                "SIMILAR_PRODUCTS",
                0.84,
                "SimilarProductsHandler",
                reasons=["similar products"],
            )
        if any(w in low for w in ["compare", "فرق", "مقایسه"]):
            return ScenarioDecision(
                "COMPARE_PRODUCTS",
                0.84,
                "CompareProductsHandler",
                reasons=["compare products"],
            )
        if any(w in low for w in ["new arrival", "جدید"]):
            return ScenarioDecision(
                "NEW_ARRIVALS",
                0.82,
                "NewArrivalsHandler",
                reasons=["new arrivals"],
            )
        if any(w in low for w in ["discount", "تخفیف"]):
            return ScenarioDecision(
                "DISCOUNT_QUESTION",
                0.84,
                "DiscountQuestionHandler",
                reasons=["discount question"],
            )

        if any(w in low for w in ["caption", "کپشن", "پست"]):
            return ScenarioDecision(
                "ADMIN_CAPTION",
                0.82,
                "AdminCaptionDraftHandler",
                reasons=["admin caption draft"],
            )
        if any(w in low for w in ["story", "استوری"]):
            return ScenarioDecision(
                "ADMIN_STORY",
                0.82,
                "AdminStoryDraftHandler",
                reasons=["admin story draft"],
            )
        if any(w in low for w in ["summary", "خلاصه مکالمه"]):
            return ScenarioDecision(
                "CONVERSATION_SUMMARY",
                0.8,
                "ConversationSummaryHandler",
                reasons=["conversation summary"],
            )

        return ScenarioDecision(
            "LLM_FALLBACK",
            0.35,
            "LLMFallbackOrchestrator",
            requires_llm=True,
            reasons=["low deterministic confidence"],
        )

    def _handler_for_catalog_plan(self, plan: Any) -> str:
        mapping = {
            "best_sellers": "BestSellersHandler",
            "similar_products": "SimilarProductsHandler",
            "price_range": "ProductSearchByPriceRangeHandler",
            "brand_listing": "ListProductsByBrandHandler",
            "category_listing": "ListProductsByCategoryHandler",
            "attribute_search": "ProductSearchByAttributesHandler",
        }
        if plan.availability_required:
            return "AvailableProductsOnlyHandler"
        return mapping.get(plan.query_type, "ListProductsByCategoryHandler")

    def _has_reference_signal(
        self, low: str, raw_provider_payload: dict[str, Any] | None
    ) -> bool:
        if raw_provider_payload and any(
            k in raw_provider_payload
            for k in ("reply_to", "story", "post", "forwarded", "reel")
        ):
            return True
        ref_words = (
            "this",
            "that",
            "same",
            "second",
            "first",
            "دوم",
            "اول",
            "همون",
            "این",
            "قبلی",
        )
        return any(w in low for w in ref_words)
