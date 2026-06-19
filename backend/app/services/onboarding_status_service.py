from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.enums import AgentMode, ChannelAccountStatus, ChannelProvider
from app.domain.models import (
    ChannelAccount,
    ColorAlias,
    Conversation,
    InstagramProductMap,
    Product,
    ProductVariant,
    Shop,
    ShopAgentSettings,
    SizeAlias,
    User,
)
from app.schemas.shop import OnboardingStatusRead, OnboardingStepStatus
from app.services.shop_service import ShopService

STEP_DEFINITIONS: tuple[tuple[str, str, str], ...] = (
    ("shop_profile", "Create shop profile", "/shops"),
    ("connect_instagram", "Connect Instagram account", "/system/channels"),
    ("first_product", "Add first product", "/products"),
    ("first_variant", "Add product variants", "/products"),
    ("map_post", "Map Instagram post URL", "/instagram-mapping"),
    ("review_aliases", "Review attribute aliases", "/catalog/attributes"),
    ("dm_simulator", "Run DM simulator test", "/simulator"),
    ("agent_mode_configured", "Configure agent mode", "/agent-studio"),
    ("auto_reply_or_copilot", "Enable auto-reply or select copilot mode", "/agent-studio"),
)

NEXT_ACTIONS: dict[str, str] = {
    "shop_profile": "Set your shop name and profile under Shop Settings.",
    "connect_instagram": "Connect an Instagram business account to receive DMs.",
    "first_product": "Add your first product to the catalog.",
    "first_variant": "Add color/size variants so the agent can resolve orders.",
    "map_post": "Map an Instagram post URL to a product for shared-post DMs.",
    "review_aliases": "Review customer-language aliases in the Attribute Dictionary.",
    "dm_simulator": "Run a DM simulator test to verify the full order flow before going live.",
    "agent_mode_configured": "Choose copilot, controlled autopilot, or human-first mode in Agent Studio.",
    "auto_reply_or_copilot": "Enable auto-send or keep copilot mode for operator-approved replies.",
}


class OnboardingStatusService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.shop_service = ShopService(db)

    def get_status(self, shop_id: UUID, user: User) -> OnboardingStatusRead:
        shop = self.shop_service.get_shop_entity(shop_id, user)
        flags = shop.onboarding_flags or {}

        account_count = self.db.scalar(
            select(func.count(ChannelAccount.id)).where(
                ChannelAccount.shop_id == shop_id,
                ChannelAccount.provider == ChannelProvider.INSTAGRAM,
                ChannelAccount.status != ChannelAccountStatus.DISABLED,
            )
        ) or 0
        product_count = self.db.scalar(
            select(func.count(Product.id)).where(Product.shop_id == shop_id)
        ) or 0
        variant_count = self.db.scalar(
            select(func.count(ProductVariant.id)).join(Product).where(Product.shop_id == shop_id)
        ) or 0
        map_count = self.db.scalar(
            select(func.count(InstagramProductMap.id)).where(InstagramProductMap.shop_id == shop_id)
        ) or 0
        color_alias_count = self.db.scalar(
            select(func.count(ColorAlias.id)).where(ColorAlias.shop_id == shop_id)
        ) or 0
        size_alias_count = self.db.scalar(
            select(func.count(SizeAlias.id)).where(SizeAlias.shop_id == shop_id)
        ) or 0
        sim_count = self.db.scalar(
            select(func.count(Conversation.id)).where(
                Conversation.shop_id == shop_id,
                Conversation.is_simulation.is_(True),
            )
        ) or 0
        agent_settings = self.db.get(ShopAgentSettings, shop_id)

        completion_checks: dict[str, bool] = {
            "shop_profile": bool(shop.name and shop.slug),
            "connect_instagram": account_count > 0,
            "first_product": product_count > 0,
            "first_variant": variant_count > 0,
            "map_post": map_count > 0,
            "review_aliases": (
                bool(flags.get("aliases_reviewed"))
                or (color_alias_count > 0 and size_alias_count > 0)
            ),
            "dm_simulator": sim_count > 0 or bool(flags.get("dm_simulator")),
            "agent_mode_configured": agent_settings is not None or bool(flags.get("agent_mode_configured")),
            "auto_reply_or_copilot": self._auto_reply_or_copilot_complete(shop, agent_settings),
        }

        steps = [
            OnboardingStepStatus(
                key=key,
                label=label,
                completed=completion_checks[key],
                href=href,
            )
            for key, label, href in STEP_DEFINITIONS
        ]
        completed_keys = [step.key for step in steps if step.completed]
        missing_keys = [step.key for step in steps if not step.completed]
        total = len(steps)
        progress = round(len(completed_keys) / total * 100) if total else 0
        next_action = (
            "All setup steps are complete. You can enable autonomous ordering when ready."
            if not missing_keys
            else NEXT_ACTIONS.get(missing_keys[0], "Continue shop setup.")
        )

        return OnboardingStatusRead(
            shop_id=shop_id,
            completed_steps=completed_keys,
            missing_steps=missing_keys,
            progress_percent=progress,
            next_recommended_action=next_action,
            steps=steps,
            total_steps=total,
        )

    @staticmethod
    def _auto_reply_or_copilot_complete(shop: Shop, agent_settings: ShopAgentSettings | None) -> bool:
        if agent_settings is not None:
            if agent_settings.mode == AgentMode.COPILOT:
                return True
            if agent_settings.auto_send_enabled:
                return True
        legacy = shop.agent_settings or {}
        return bool(legacy.get("auto_reply_enabled"))
