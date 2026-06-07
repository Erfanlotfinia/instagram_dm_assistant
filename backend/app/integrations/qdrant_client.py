from __future__ import annotations

import logging
from typing import Any, Protocol
from uuid import UUID

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


class QdrantSearchHit:
    def __init__(self, product_id: UUID, score: float, payload: dict[str, Any]) -> None:
        self.product_id = product_id
        self.score = score
        self.payload = payload


class QdrantClient(Protocol):
    def ensure_collection(self, vector_size: int) -> None: ...

    def upsert_product(
        self,
        product_id: UUID,
        vector: list[float],
        payload: dict[str, Any],
    ) -> None: ...

    def search(self, vector: list[float], limit: int) -> list[QdrantSearchHit]: ...


class LiveQdrantClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def _client(self):
        from qdrant_client import QdrantClient as QdrantSDK

        return QdrantSDK(url=self.settings.qdrant_url)

    def ensure_collection(self, vector_size: int) -> None:
        from qdrant_client.http import models as qmodels

        client = self._client()
        collection = self.settings.qdrant_collection_name
        if client.collection_exists(collection):
            return
        client.create_collection(
            collection_name=collection,
            vectors_config=qmodels.VectorParams(size=vector_size, distance=qmodels.Distance.COSINE),
        )

    def upsert_product(
        self,
        product_id: UUID,
        vector: list[float],
        payload: dict[str, Any],
    ) -> None:
        from qdrant_client.http import models as qmodels

        client = self._client()
        client.upsert(
            collection_name=self.settings.qdrant_collection_name,
            points=[
                qmodels.PointStruct(
                    id=str(product_id),
                    vector=vector,
                    payload={**payload, "product_id": str(product_id)},
                )
            ],
        )

    def search(self, vector: list[float], limit: int) -> list[QdrantSearchHit]:
        client = self._client()
        results = client.search(
            collection_name=self.settings.qdrant_collection_name,
            query_vector=vector,
            limit=limit,
        )
        hits: list[QdrantSearchHit] = []
        for result in results:
            product_id_raw = result.payload.get("product_id") if result.payload else None
            if not product_id_raw:
                continue
            hits.append(
                QdrantSearchHit(
                    product_id=UUID(str(product_id_raw)),
                    score=float(result.score),
                    payload=dict(result.payload or {}),
                )
            )
        return hits


class MockQdrantClient:
    def __init__(self) -> None:
        self.points: dict[str, tuple[list[float], dict[str, Any]]] = {}

    def ensure_collection(self, vector_size: int) -> None:
        return None

    def upsert_product(
        self,
        product_id: UUID,
        vector: list[float],
        payload: dict[str, Any],
    ) -> None:
        self.points[str(product_id)] = (vector, payload)

    def search(self, vector: list[float], limit: int) -> list[QdrantSearchHit]:
        scored: list[QdrantSearchHit] = []
        for product_id, (stored_vector, payload) in self.points.items():
            score = _cosine_similarity(vector, stored_vector)
            scored.append(
                QdrantSearchHit(
                    product_id=UUID(product_id),
                    score=score,
                    payload=payload,
                )
            )
        scored.sort(key=lambda hit: hit.score, reverse=True)
        return scored[:limit]


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
