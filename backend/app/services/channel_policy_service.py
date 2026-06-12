from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.domain.enums import ChannelProvider
from app.schemas.channels import NormalizedOutboundMessage


@dataclass(frozen=True)
class ChannelPolicyDecision:
    allowed: bool
    reason: str | None = None
    requires_template: bool = False


class ChannelPolicyService:
    def evaluate_outbound(
        self,
        message: NormalizedOutboundMessage,
        messaging_window_expires_at: datetime | None = None,
    ) -> ChannelPolicyDecision:
        if message.provider == ChannelProvider.WHATSAPP:
            if (
                messaging_window_expires_at
                and datetime.now(tz=messaging_window_expires_at.tzinfo)
                > messaging_window_expires_at
                and not message.template_name
            ):
                return ChannelPolicyDecision(
                    False, "whatsapp_template_required_outside_customer_service_window", True
                )
            return ChannelPolicyDecision(True)
        if (
            message.provider in {ChannelProvider.TELEGRAM, ChannelProvider.BALE}
            and not message.external_chat_id
        ):
            return ChannelPolicyDecision(False, "bot_chat_must_have_interacted_or_be_allowed")
        if message.provider == ChannelProvider.RUBIKA and message.metadata.get(
            "webhook_url", "https://"
        ).startswith("http://"):
            return ChannelPolicyDecision(False, "rubika_endpoint_mode_requires_https")
        return ChannelPolicyDecision(True)
