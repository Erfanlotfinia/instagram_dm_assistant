from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.domain.enums import AgentIntent, AgentWorkflowState
from app.domain.models import ConversationSlots, Product, ProductVariant

FIELD_LABELS_FA = {
    "product": "محصول",
    "color": "رنگ",
    "size": "سایز",
    "quantity": "تعداد",
    "customer_name": "نام",
    "phone": "شماره تماس",
    "city": "شهر",
    "address": "آدرس",
    "postal_code": "کد پستی",
    "stock": "موجودی",
}


@dataclass
class ReplyFacts:
    intent: AgentIntent
    workflow_state: AgentWorkflowState
    product: Product | None
    variant: ProductVariant | None
    slots: ConversationSlots
    missing_fields: list[str]
    valid_colors: list[str]
    valid_sizes: list[str]
    available_stock: int | None
    handoff_reason: str | None = None
    invalid_color: bool = False
    invalid_size: bool = False
    style_hint: str | None = None
    payment_url: str | None = None
    order_total: str | None = None
    order_currency: str | None = None
    upsell_text: str | None = None
    size_confirmation_needed: bool = False


class ResponseGenerationService:
    def generate(self, facts: ReplyFacts) -> str:
        if facts.workflow_state == AgentWorkflowState.HUMAN_HANDOFF:
            return "لطفاً چند لحظه صبر کنید. یکی از همکاران ما به زودی پاسخ می‌دهد."

        if facts.workflow_state == AgentWorkflowState.CANCELLED:
            return "سفارش شما لغو شد. هر زمان خواستید دوباره پیام بدهید."

        if facts.workflow_state == AgentWorkflowState.WAITING_FOR_PRODUCT:
            return "برای ادامه، لطفاً پست اینستاگرام محصول مورد نظرتان را ارسال کنید یا نام محصول را بنویسید."

        if facts.workflow_state == AgentWorkflowState.WAITING_FOR_VARIANT:
            if "size_confirmation" in facts.missing_fields or facts.size_confirmation_needed:
                size = facts.slots.size or "—"
                return (
                    f"سایز قبلی شما {size} بود. همین سایز را تأیید می‌کنید؟ "
                    "در صورت تأیید «بله» بفرستید یا سایز دیگری را مشخص کنید."
                )
            if facts.invalid_color or facts.invalid_size:
                colors = "، ".join(facts.valid_colors) if facts.valid_colors else "نامشخص"
                sizes = "، ".join(facts.valid_sizes) if facts.valid_sizes else "نامشخص"
                return (
                    f"رنگ یا سایز انتخابی معتبر نیست. رنگ‌های موجود: {colors}. "
                    f"سایزهای موجود: {sizes}. لطفاً دوباره مشخص کنید."
                )
            if facts.available_stock == 0:
                title = facts.product.title if facts.product else "این محصول"
                return f"متأسفانه {title} در حال حاضر موجود نیست."

            title = facts.product.title if facts.product else "محصول"
            colors = "، ".join(facts.valid_colors) if facts.valid_colors else "نامشخص"
            sizes = "، ".join(facts.valid_sizes) if facts.valid_sizes else "نامشخص"
            return (
                f"محصول «{title}» پیدا شد. لطفاً رنگ و سایز را مشخص کنید.\n"
                f"رنگ‌های موجود: {colors}\n"
                f"سایزهای موجود: {sizes}"
            )

        if facts.workflow_state == AgentWorkflowState.WAITING_FOR_CUSTOMER_INFO:
            missing_labels = [FIELD_LABELS_FA.get(field, field) for field in facts.missing_fields]
            title = facts.product.title if facts.product else "محصول"
            price_text = _format_price(facts.variant, facts.product)
            stock_text = (
                f"موجودی: {facts.available_stock}"
                if facts.available_stock is not None
                else "موجودی: نامشخص"
            )
            return (
                f"عالی! {title} - {facts.slots.color or ''} سایز {facts.slots.size or ''} - "
                f"{price_text} ({stock_text}).\n"
                f"برای تکمیل سفارش لطفاً این موارد را بفرستید: { '، '.join(missing_labels) }."
            )

        if facts.workflow_state == AgentWorkflowState.WAITING_FOR_CONFIRMATION:
            return _order_summary(facts, confirm_prompt=True)

        if facts.workflow_state == AgentWorkflowState.WAITING_FOR_PAYMENT:
            summary = _order_summary(facts, confirm_prompt=False)
            if facts.payment_url:
                return summary + f"\n\nلینک پرداخت:\n{facts.payment_url}"
            return summary + "\nلطفاً پرداخت را انجام دهید."

        if facts.workflow_state == AgentWorkflowState.PAID:
            total = facts.order_total or "—"
            currency = facts.order_currency or ""
            return f"پرداخت شما تأیید شد. مبلغ {total} {currency}. به زودی سفارش ارسال می‌شود."

        if facts.intent in {AgentIntent.ASK_PRICE, AgentIntent.ASK_STOCK}:
            return _price_stock_reply(facts)

        return "پیام شما دریافت شد. لطفاً کمی بیشتر توضیح دهید تا بتوانم کمک کنم."


def _format_price(variant: ProductVariant | None, product: Product | None) -> str:
    if variant is not None:
        return f"قیمت: {variant.price} {product.currency if product else ''}".strip()
    if product is not None:
        return f"قیمت: {product.base_price} {product.currency}"
    return "قیمت: نامشخص"


def _order_summary(facts: ReplyFacts, *, confirm_prompt: bool) -> str:
    title = facts.product.title if facts.product else "محصول"
    quantity = facts.slots.quantity or 1
    price = facts.variant.price if facts.variant else (facts.product.base_price if facts.product else Decimal("0"))
    total = Decimal(str(price)) * quantity
    currency = facts.product.currency if facts.product else ""
    lines = [
        "خلاصه سفارش:",
        f"- محصول: {title}",
        f"- رنگ: {facts.slots.color or '-'}",
        f"- سایز: {facts.slots.size or '-'}",
        f"- تعداد: {quantity}",
        f"- نام: {facts.slots.customer_name or '-'}",
        f"- تلفن: {facts.slots.phone or '-'}",
        f"- شهر: {facts.slots.city or '-'}",
        f"- آدرس: {facts.slots.address or '-'}",
        f"- مبلغ: {total} {currency}".strip(),
    ]
    if confirm_prompt:
        lines.append("آیا سفارش را تأیید می‌کنید؟ (بله/تأیید)")
    return "\n".join(lines)


def _price_stock_reply(facts: ReplyFacts) -> str:
    title = facts.product.title if facts.product else "محصول"
    price_text = _format_price(facts.variant, facts.product)
    stock_text = facts.available_stock if facts.available_stock is not None else "نامشخص"
    return f"{title}: {price_text}. موجودی: {stock_text}."
