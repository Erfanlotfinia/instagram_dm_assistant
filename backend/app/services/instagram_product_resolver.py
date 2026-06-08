from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.domain.models import InstagramProductMap, User
from app.repositories.instagram_account_repository import InstagramAccountRepository
from app.repositories.instagram_product_map_repository import InstagramProductMapRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.instagram_product_map import (
    InstagramProductMapCreate,
    InstagramProductMapRead,
    InstagramProductMapUpdate,
    ResolveInstagramProductRequest,
    ProductCandidate,
    ResolveInstagramProductResponse,
)
from app.schemas.product import ProductRead
from app.services.audit_service import AuditService
from app.services.shop_service import ShopService


def normalize_instagram_post_url(url: str) -> str:
    return url.strip().rstrip("/")


class InstagramProductResolver:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.maps = InstagramProductMapRepository(db)
        self.products = ProductRepository(db)
        self.accounts = InstagramAccountRepository(db)
        self.shop_service = ShopService(db)

    def list_maps(self, shop_id: UUID, user: User) -> list[InstagramProductMapRead]:
        self.shop_service.get_shop(shop_id, user)
        mappings = self.maps.list_for_shop(shop_id)
        return [InstagramProductMapRead.model_validate(m) for m in mappings]

    def create_map(
        self,
        shop_id: UUID,
        payload: InstagramProductMapCreate,
        user: User,
    ) -> InstagramProductMapRead:
        self.shop_service.get_shop(shop_id, user)
        self._validate_product(shop_id, payload.product_id)
        self._validate_instagram_account(shop_id, payload.instagram_account_id)

        mapping = InstagramProductMap(
            shop_id=shop_id,
            instagram_account_id=payload.instagram_account_id,
            instagram_media_id=payload.instagram_media_id,
            instagram_post_url=normalize_instagram_post_url(payload.instagram_post_url),
            product_id=payload.product_id,
            confidence_source=payload.confidence_source,
            is_active=payload.is_active,
            display_order=payload.display_order,
            admin_label=payload.admin_label,
            visual_hint=payload.visual_hint,
            caption_hint=payload.caption_hint,
            is_primary=payload.is_primary,
        )
        created = self.maps.create(mapping)
        self.maps.commit()
        self.maps.refresh(created)
        AuditService(self.db).log(
            action="product_mapping_created",
            entity_type="instagram_product_map",
            shop_id=shop_id,
            actor_user_id=user.id,
            entity_id=str(created.id),
            metadata={"product_id": str(payload.product_id), "instagram_post_url": created.instagram_post_url},
        )
        self.maps.commit()
        return InstagramProductMapRead.model_validate(created)

    def update_map(
        self,
        shop_id: UUID,
        map_id: UUID,
        payload: InstagramProductMapUpdate,
        user: User,
    ) -> InstagramProductMapRead:
        self.shop_service.get_shop(shop_id, user)
        mapping = self._get_map_or_404(shop_id, map_id)
        updates = payload.model_dump(exclude_unset=True)

        if "product_id" in updates and updates["product_id"] is not None:
            self._validate_product(shop_id, updates["product_id"])
        if "instagram_post_url" in updates and updates["instagram_post_url"] is not None:
            updates["instagram_post_url"] = normalize_instagram_post_url(updates["instagram_post_url"])

        for field, value in updates.items():
            setattr(mapping, field, value)

        self.maps.commit()
        self.maps.refresh(mapping)
        AuditService(self.db).log(
            action="product_mapping_updated",
            entity_type="instagram_product_map",
            shop_id=shop_id,
            actor_user_id=user.id,
            entity_id=str(mapping.id),
            metadata=updates,
        )
        self.maps.commit()
        return InstagramProductMapRead.model_validate(mapping)

    def resolve(
        self,
        shop_id: UUID,
        payload: ResolveInstagramProductRequest,
        user: User,
    ) -> ResolveInstagramProductResponse:
        self.shop_service.get_shop(shop_id, user)
        return self.resolve_internal(shop_id, payload)

    def resolve_internal(
        self,
        shop_id: UUID,
        payload: ResolveInstagramProductRequest,
    ) -> ResolveInstagramProductResponse:
        mappings: list[InstagramProductMap] = []
        if payload.instagram_media_id:
            mappings = self.maps.list_active_by_media_id(shop_id, payload.instagram_media_id)
        if not mappings and payload.instagram_post_url:
            normalized_url = normalize_instagram_post_url(payload.instagram_post_url)
            mappings = self.maps.list_active_by_post_url(shop_id, normalized_url)

        mappings = sorted([m for m in mappings if m.product is not None], key=lambda m: (not m.is_primary, m.display_order, m.created_at))
        if not mappings:
            return ResolveInstagramProductResponse(product=None)

        candidates = [
            ProductCandidate(
                product=ProductRead.model_validate(mapping.product),
                map_id=mapping.id,
                confidence_source=mapping.confidence_source,
                admin_label=mapping.admin_label,
                visual_hint=mapping.visual_hint,
                caption_hint=mapping.caption_hint,
                is_primary=mapping.is_primary,
            )
            for mapping in mappings
        ]
        if len(candidates) > 1:
            return ResolveInstagramProductResponse(
                product=None,
                candidates=candidates,
                requires_product_selection=True,
            )
        mapping = mappings[0]
        return ResolveInstagramProductResponse(
            product=ProductRead.model_validate(mapping.product),
            map_id=mapping.id,
            confidence_source=mapping.confidence_source,
            candidates=candidates,
            requires_product_selection=False,
        )

    def _get_map_or_404(self, shop_id: UUID, map_id: UUID) -> InstagramProductMap:
        mapping = self.maps.get_for_shop(shop_id, map_id)
        if mapping is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mapping not found")
        return mapping

    def _validate_product(self, shop_id: UUID, product_id: UUID) -> None:
        product = self.products.get_for_shop(shop_id, product_id)
        if product is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    def _validate_instagram_account(self, shop_id: UUID, account_id: UUID) -> None:
        accounts = self.accounts.list_for_shop(shop_id)
        if not any(account.id == account_id for account in accounts):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Instagram account not found for this shop",
            )
