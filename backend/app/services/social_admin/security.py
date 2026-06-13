from __future__ import annotations
import base64, hashlib, hmac, json
from dataclasses import dataclass
from datetime import datetime, timezone

@dataclass
class SignedAction:
    action_id: str; shop_id: str; conversation_id: str; context_item_id: str | None; action_type: str; expires_at: str; signature: str
class SignedActionService:
    def __init__(self, secret: str) -> None: self.secret = secret.encode()
    def _sig(self, payload: dict) -> str:
        body = json.dumps({k:v for k,v in payload.items() if k != "signature"}, sort_keys=True, separators=(",", ":")).encode()
        return base64.urlsafe_b64encode(hmac.new(self.secret, body, hashlib.sha256).digest()).decode().rstrip("=")
    def sign(self, payload: dict) -> dict:
        data = dict(payload); data["signature"] = self._sig(data); return data
    def verify(self, payload: dict, shop_id: str, conversation_id: str) -> bool:
        if payload.get("shop_id") != shop_id or payload.get("conversation_id") != conversation_id: return False
        if datetime.fromisoformat(payload["expires_at"].replace("Z", "+00:00")) < datetime.now(timezone.utc): return False
        return hmac.compare_digest(payload.get("signature", ""), self._sig(payload))
