from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

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
    def can_handle(self, context: dict[str, Any]) -> HandlerDecision: return HandlerDecision(True, .75, [self.scenario_code])
    def handle(self, context: dict[str, Any]) -> HandlerResult: return HandlerResult("handled", response_text="Handled deterministically.", confidence=.75, audit_metadata={"handler": self.__class__.__name__, "llm_used": False})

def make_handler(name: str, response: str, status: str = "handled"):
    return type(name, (BaseAutomationHandler,), {"handle": lambda self, context: HandlerResult(status, response_text=response, confidence=.8, audit_metadata={"handler": name, "llm_used": False})})

_NAMES = "AskPriceReferencedProductHandler AskStockReferencedProductHandler AskDetailsReferencedProductHandler BuyReferencedProductHandler SelectFromProductListHandler AmbiguousReferenceClarificationHandler ListProductsByCategoryHandler ListProductsByBrandHandler ProductSearchByAttributesHandler ProductSearchByPriceRangeHandler SimilarProductsHandler CompareProductsHandler BestSellersHandler AvailableProductsOnlyHandler StartOrderHandler AddItemHandler RemoveItemHandler ChangeQuantityHandler ChangeAttributeHandler OrderSummaryHandler ConfirmOrderHandler CancelOrderHandler EditOrderHandler PaymentMethodsHandler SendPaymentLinkHandler ManualPaymentReceiptHandler PaymentStatusHandler PaymentFailedHandler SuspiciousPaymentHandoffHandler ShippingCostHandler ShippingMethodsHandler DeliveryTimeHandler AddressCaptureHandler AddressChangeHandler TrackingCodeHandler OrderStatusHandler DeliveryComplaintHandler PolicyQuestionHandler ReturnRequestHandler ExchangeRequestHandler ComplaintHandler HumanRequestHandler OffTopicHandler SpamAbuseHandler NewArrivalsHandler DiscountQuestionHandler CampaignQuestionHandler CatalogExportHandler AdminReplySuggestionHandler AdminCaptionDraftHandler AdminStoryDraftHandler ConversationSummaryHandler FAQMiningHandler".split()
globals().update({n: make_handler(n, n.replace("Handler", " handled")) for n in _NAMES})

class AutomationHandlerRegistry:
    def __init__(self) -> None:
        self.handlers = {n: globals()[n]() for n in _NAMES}
    def get(self, name: str) -> BaseAutomationHandler | None: return self.handlers.get(name)
    def dispatch(self, name: str, context: dict[str, Any]) -> HandlerResult:
        handler = self.get(name)
        if not handler: return HandlerResult("needs_human", handoff_reason="No registered handler", confidence=0)
        decision = handler.can_handle(context)
        if not decision.can_handle or decision.confidence < .5: return HandlerResult("needs_clarification", response_text="Can you clarify?", confidence=decision.confidence)
        return handler.handle(context)
