from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

@dataclass
class ScenarioDecision:
    scenario_code: str
    confidence: float
    handler: str
    requires_llm: bool = False
    requires_handoff: bool = False
    reasons: list[str] = field(default_factory=list)

class ScenarioRouter:
    def route(self, message: Any, conversation_context: Any = None, customer_profile: Any = None, active_order: Any = None, channel_capabilities: Any = None, shop_settings: Any = None) -> ScenarioDecision:
        text = (getattr(message, "text", None) or (message.get("text") if isinstance(message, dict) else "") or "").lower()
        payload = getattr(message, "payload", None) or (message.get("payload") if isinstance(message, dict) else None)
        if payload: return ScenarioDecision("BUTTON_CALLBACK", .99, "SelectFromProductListHandler", reasons=["button/callback payload"])
        if text.startswith("/"): return ScenarioDecision("EXPLICIT_COMMAND", .96, "CatalogExportHandler", reasons=["explicit command"])
        if active_order and any(w in text for w in ["cancel","لغو"]): return ScenarioDecision("ORDER_CANCEL", .92, "CancelOrderHandler", reasons=["active order cancellation"])
        if active_order and any(w in text for w in ["summary","خلاصه"]): return ScenarioDecision("ORDER_SUMMARY", .92, "OrderSummaryHandler", reasons=["active order summary"])
        if active_order and any(w in text for w in ["confirm","تایید"]): return ScenarioDecision("ORDER_CONFIRM", .9, "ConfirmOrderHandler", reasons=["active order confirmation"])
        if any(w in text for w in ["price","قیمت","چند"]): return ScenarioDecision("ASK_PRICE_REFERENCED_PRODUCT", .88, "AskPriceReferencedProductHandler", reasons=["deterministic price keyword"])
        if any(w in text for w in ["stock","available","موجود"]): return ScenarioDecision("ASK_STOCK_REFERENCED_PRODUCT", .88, "AskStockReferencedProductHandler", reasons=["deterministic stock keyword"])
        if any(w in text for w in ["buy","میخوام","می‌خوام","بده"]): return ScenarioDecision("BUY_REFERENCED_PRODUCT", .86, "BuyReferencedProductHandler", reasons=["deterministic buy keyword"])
        if any(w in text for w in ["human","admin","اپراتور"]): return ScenarioDecision("HUMAN_REQUEST", .98, "HumanRequestHandler", requires_handoff=True, reasons=["human requested"])
        if any(w in text for w in ["complaint","angry","ناراضی","شکایت"]): return ScenarioDecision("COMPLAINT", .8, "ComplaintHandler", requires_handoff=True, reasons=["complaint risk"])
        return ScenarioDecision("LLM_FALLBACK", .35, "LLMFallbackOrchestrator", requires_llm=True, reasons=["low deterministic confidence"])
