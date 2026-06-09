from __future__ import annotations

import logging
from typing import Any, Protocol
from uuid import UUID

from app.core.config import Settings, get_settings
from app.integrations.catalog_hybrid_search import (
    HybridSearchHit,
    apply_business_rerank,
    build_sparse_vector,
    fuse_hybrid_results,
    sparse_similarity,
)

logger = logging.getLogger(__name__)


class QdrantSearchHit:
    def __init__(self, product_id: UUID, score: float, payload: dict[str, Any]) -> None:
        self.product_id = product_id
        self.score = score
        self.payload = payload


class QdrantClient(Protocol):
    def ensure_collection(self, vector_size: int) -> None: ...

    def ensure_variants_collection(self, vector_size: int) -> None: ...

    def upsert_product(
        self,
        product_id: UUID,
        vector: list[float],
        payload: dict[str, Any],
        sparse_text: str | None = None,
    ) -> None: ...

    def upsert_variant(
        self,
        variant_id: UUID,
        vector: list[float],
        payload: dict[str, Any],
        sparse_text: str | None = None,
    ) -> None: ...

    def search(self, vector: list[float], limit: int, collection: str = "products") -> list[QdrantSearchHit]: ...

    def hybrid_search(
        self,
        *,
        query_vector: list[float],
        query_text: str,
        limit: int,
        shop_id: UUID | None = None,
        collection: str = "products",
        fusion_strategy: str = "rrf",
        rrf_k: int = 60,
        filters: dict[str, Any] | None = None,
        apply_rerank: bool = True,
    ) -> list[HybridSearchHit]: ...


class LiveQdrantClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def _client(self):
        from qdrant_client import QdrantClient as QdrantSDK

        return QdrantSDK(url=self.settings.qdrant_url)

    def _collection_name(self, collection: str) -> str:
        if collection == "variants":
            return self.settings.qdrant_variants_collection_name
        return self.settings.qdrant_collection_name

    def ensure_collection(self, vector_size: int) -> None:
        self._ensure_named_collection(self.settings.qdrant_collection_name, vector_size)

    def ensure_variants_collection(self, vector_size: int) -> None:
        self._ensure_named_collection(self.settings.qdrant_variants_collection_name, vector_size)

    def _ensure_named_collection(self, collection: str, vector_size: int) -> None:
        from qdrant_client.http import models as qmodels

        client = self._client()
        if client.collection_exists(collection):
            existing_size = self._existing_vector_size(client, collection)
            if existing_size == vector_size:
                return
            logger.warning(
                "Recreating Qdrant collection '%s' due to vector size mismatch (existing=%s, expected=%s)",
                collection,
                existing_size,
                vector_size,
            )
            client.delete_collection(collection)
        client.create_collection(
            collection_name=collection,
            vectors_config=qmodels.VectorParams(size=vector_size, distance=qmodels.Distance.COSINE),
        )

    @staticmethod
    def _existing_vector_size(client, collection: str) -> int | None:
        try:
            info = client.get_collection(collection)
            params = info.config.params.vectors
            # Unnamed (single) vector config exposes `.size` directly.
            return getattr(params, "size", None)
        except Exception:  # noqa: BLE001
            return None

    def upsert_product(
        self,
        product_id: UUID,
        vector: list[float],
        payload: dict[str, Any],
        sparse_text: str | None = None,
    ) -> None:
        self._upsert_point(
            collection=self.settings.qdrant_collection_name,
            point_id=str(product_id),
            vector=vector,
            payload={**payload, "product_id": str(product_id), "sparse_text": sparse_text or ""},
        )

    def upsert_variant(
        self,
        variant_id: UUID,
        vector: list[float],
        payload: dict[str, Any],
        sparse_text: str | None = None,
    ) -> None:
        self._upsert_point(
            collection=self.settings.qdrant_variants_collection_name,
            point_id=str(variant_id),
            vector=vector,
            payload={**payload, "variant_id": str(variant_id), "sparse_text": sparse_text or ""},
        )

    def _upsert_point(
        self,
        *,
        collection: str,
        point_id: str,
        vector: list[float],
        payload: dict[str, Any],
    ) -> None:
        from qdrant_client.http import models as qmodels

        client = self._client()
        client.upsert(
            collection_name=collection,
            points=[qmodels.PointStruct(id=point_id, vector=vector, payload=payload)],
        )

    def search(self, vector: list[float], limit: int, collection: str = "products") -> list[QdrantSearchHit]:
        collection_name = self._collection_name(collection)
        client = self._client()
        if not client.collection_exists(collection_name):
            return []
        response = client.query_points(
            collection_name=collection_name,
            query=vector,
            limit=limit,
            with_payload=True,
        )
        return self._to_product_hits(response.points, collection=collection)

    def hybrid_search(
        self,
        *,
        query_vector: list[float],
        query_text: str,
        limit: int,
        shop_id: UUID | None = None,
        collection: str = "products",
        fusion_strategy: str = "rrf",
        rrf_k: int = 60,
        filters: dict[str, Any] | None = None,
        apply_rerank: bool = True,
    ) -> list[HybridSearchHit]:
        dense_hits = self.search(query_vector, limit=max(limit * 3, 10), collection=collection)
        if shop_id is not None:
            dense_hits = [hit for hit in dense_hits if hit.payload.get("shop_id") == str(shop_id)]

        dense_ranked = [(hit.product_id, hit.score) for hit in dense_hits]
        query_sparse = build_sparse_vector(query_text)
        sparse_ranked: list[tuple[UUID, float]] = []
        for hit in dense_hits:
            doc_sparse = build_sparse_vector(str(hit.payload.get("sparse_text") or hit.payload.get("title") or ""))
            sparse_ranked.append((hit.product_id, sparse_similarity(query_sparse, doc_sparse)))
        sparse_ranked.sort(key=lambda item: item[1], reverse=True)

        fused = fuse_hybrid_results(
            dense_ranked,
            sparse_ranked,
            strategy="dbsf" if fusion_strategy == "dbsf" else "rrf",
            rrf_k=rrf_k,
        )
        dense_map = {hit.product_id: hit for hit in dense_hits}
        sparse_map = dict(sparse_ranked)
        hybrid_hits: list[HybridSearchHit] = []
        id_field = "variant_id" if collection == "variants" else "product_id"
        for entity_id, fused_score in fused[: limit * 2]:
            dense_hit = dense_map.get(entity_id)
            payload = dense_hit.payload if dense_hit is not None else {id_field: str(entity_id)}
            if filters:
                if shop_id and payload.get("shop_id") != str(shop_id):
                    continue
                for key, value in filters.items():
                    if payload.get(key) != value:
                        break
                else:
                    pass
                if any(payload.get(key) != value for key, value in filters.items()):
                    continue
            hybrid_hits.append(
                HybridSearchHit(
                    entity_id=entity_id,
                    dense_score=dense_hit.score if dense_hit is not None else 0.0,
                    sparse_score=sparse_map.get(entity_id, 0.0),
                    fused_score=fused_score,
                    payload=payload,
                )
            )
        if apply_rerank:
            hybrid_hits = apply_business_rerank(hybrid_hits)
        return hybrid_hits[:limit]

    @staticmethod
    def _to_product_hits(results, collection: str = "products") -> list[QdrantSearchHit]:
        id_field = "variant_id" if collection == "variants" else "product_id"
        hits: list[QdrantSearchHit] = []
        for result in results:
            payload = dict(result.payload or {})
            entity_id_raw = payload.get(id_field) or result.id
            if not entity_id_raw:
                continue
            hits.append(
                QdrantSearchHit(
                    product_id=UUID(str(entity_id_raw)),
                    score=float(result.score),
                    payload=payload,
                )
            )
        return hits


class MockQdrantClient:
    def __init__(self) -> None:
        self.points: dict[str, tuple[list[float], dict[str, Any], str]] = {}
        self.variant_points: dict[str, tuple[list[float], dict[str, Any], str]] = {}

    def ensure_collection(self, vector_size: int) -> None:
        return None

    def ensure_variants_collection(self, vector_size: int) -> None:
        return None

    def upsert_product(
        self,
        product_id: UUID,
        vector: list[float],
        payload: dict[str, Any],
        sparse_text: str | None = None,
    ) -> None:
        self.points[str(product_id)] = (vector, payload, sparse_text or "")

    def upsert_variant(
        self,
        variant_id: UUID,
        vector: list[float],
        payload: dict[str, Any],
        sparse_text: str | None = None,
    ) -> None:
        self.variant_points[str(variant_id)] = (vector, payload, sparse_text or "")

    def search(self, vector: list[float], limit: int, collection: str = "products") -> list[QdrantSearchHit]:
        store = self.variant_points if collection == "variants" else self.points
        scored: list[QdrantSearchHit] = []
        for entity_id, (stored_vector, payload, _sparse) in store.items():
            score = _cosine_similarity(vector, stored_vector)
            scored.append(
                QdrantSearchHit(
                    product_id=UUID(entity_id),
                    score=score,
                    payload=payload,
                )
            )
        scored.sort(key=lambda hit: hit.score, reverse=True)
        return scored[:limit]

    def hybrid_search(
        self,
        *,
        query_vector: list[float],
        query_text: str,
        limit: int,
        shop_id: UUID | None = None,
        collection: str = "products",
        fusion_strategy: str = "rrf",
        rrf_k: int = 60,
        filters: dict[str, Any] | None = None,
        apply_rerank: bool = True,
    ) -> list[HybridSearchHit]:
        store = self.variant_points if collection == "variants" else self.points
        id_key = "variant_id" if collection == "variants" else "product_id"
        dense_ranked: list[tuple[UUID, float]] = []
        sparse_ranked: list[tuple[UUID, float]] = []
        payloads: dict[UUID, dict[str, Any]] = {}
        query_sparse = build_sparse_vector(query_text)

        for point_id, (stored_vector, payload, sparse_text) in store.items():
            entity_id = UUID(point_id)
            if shop_id is not None and payload.get("shop_id") != str(shop_id):
                continue
            if filters:
                if any(payload.get(key) != value for key, value in filters.items()):
                    continue
            dense_score = _cosine_similarity(query_vector, stored_vector)
            sparse_score = sparse_similarity(query_sparse, build_sparse_vector(sparse_text or payload.get("title", "")))
            dense_ranked.append((entity_id, dense_score))
            sparse_ranked.append((entity_id, sparse_score))
            payloads[entity_id] = {**payload, id_key: point_id}

        dense_ranked.sort(key=lambda item: item[1], reverse=True)
        sparse_ranked.sort(key=lambda item: item[1], reverse=True)
        fused = fuse_hybrid_results(
            dense_ranked,
            sparse_ranked,
            strategy="dbsf" if fusion_strategy == "dbsf" else "rrf",
            rrf_k=rrf_k,
        )
        dense_map = dict(dense_ranked)
        sparse_map = dict(sparse_ranked)
        hits = [
            HybridSearchHit(
                entity_id=entity_id,
                dense_score=dense_map.get(entity_id, 0.0),
                sparse_score=sparse_map.get(entity_id, 0.0),
                fused_score=score,
                payload=payloads[entity_id],
            )
            for entity_id, score in fused[: limit * 2]
        ]
        if apply_rerank:
            hits = apply_business_rerank(hits)
        return hits[:limit]


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    size = min(len(left), len(right))
    if size == 0:
        return 0.0
    dot = sum(left[index] * right[index] for index in range(size))
    left_norm = sum(value * value for value in left[:size]) ** 0.5
    right_norm = sum(value * value for value in right[:size]) ** 0.5
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)
