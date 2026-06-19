from __future__ import annotations

from typing import Any, Protocol

from fastapi import Request

from app.schemas.channels import (
    ChannelCapabilities,
    NormalizedInboundMessage,
    NormalizedOutboundMessage,
    ProviderSendResult,
)


class TelegramChannelAdapter(Protocol):
  async def verify_webhook(self, request: Request) -> bool: ...

  def receive_message(
      self, payload: dict[str, Any], headers: dict[str, str] | None = None
  ) -> list[NormalizedInboundMessage]: ...

  async def send_message(
      self, message: NormalizedOutboundMessage, account: Any | None = None
  ) -> ProviderSendResult: ...

  async def mark_read(
      self,
      external_chat_id: str,
      external_message_id: str,
      business_connection_id: str | None = None,
  ) -> ProviderSendResult: ...

  async def sync_metadata(self, account: Any) -> dict[str, Any]: ...

  async def validate_connection(self, account: Any | None = None) -> bool: ...

  def get_capabilities(self, account: Any | None = None) -> ChannelCapabilities: ...

  def parse_inbound_update(
      self, payload: dict[str, Any], headers: dict[str, str] | None = None
  ) -> list[NormalizedInboundMessage]: ...

  async def validate_credentials(self) -> bool: ...

  async def configure_webhook(self, webhook_url: str, secret: str | None = None) -> dict[str, Any]: ...

  async def delete_webhook(self) -> dict[str, Any]: ...

  async def get_webhook_info(self) -> dict[str, Any]: ...
