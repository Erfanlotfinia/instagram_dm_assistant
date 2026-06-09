from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from math import log1p
from typing import Any, Literal
from uuid import UUID

FusionStrategy = Literal["rrf", "dbsf"]


@dataclass(frozen=True)
class HybridSearchHit:
    entity_id: UUID
    dense_score: float
    sparse_score: float
    fused_score: float
    payload: dict[str, Any]
    rank_dense: int | None = None
    rank_sparse: int | None = None


def tokenize_for_sparse(text: str) -> list[str]:
    cleaned = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in text.casefold())
    return [token for token in cleaned.split() if len(token) >= 2]


def build_sparse_vector(text: str) -> dict[str, float]:
    tokens = tokenize_for_sparse(text)
    counts = Counter(tokens)
    total = sum(counts.values()) or 1
    return {token: count / total for token, count in counts.items()}


def sparse_similarity(query_vec: dict[str, float], doc_vec: dict[str, float]) -> float:
    if not query_vec or not doc_vec:
        return 0.0
    shared = set(query_vec) & set(doc_vec)
    if not shared:
        return 0.0
    dot = sum(query_vec[t] * doc_vec[t] for t in shared)
    q_norm = sum(v * v for v in query_vec.values()) ** 0.5
    d_norm = sum(v * v for v in doc_vec.values()) ** 0.5
    if q_norm == 0 or d_norm == 0:
        return 0.0
    return dot / (q_norm * d_norm)


def reciprocal_rank_fusion(
    dense_ranked: list[tuple[UUID, float]],
    sparse_ranked: list[tuple[UUID, float]],
    *,
    k: int = 60,
) -> dict[UUID, float]:
    scores: dict[UUID, float] = {}
    for rank, (entity_id, _) in enumerate(dense_ranked, start=1):
        scores[entity_id] = scores.get(entity_id, 0.0) + 1.0 / (k + rank)
    for rank, (entity_id, _) in enumerate(sparse_ranked, start=1):
        scores[entity_id] = scores.get(entity_id, 0.0) + 1.0 / (k + rank)
    return scores


def distribution_based_score_fusion(
    dense_ranked: list[tuple[UUID, float]],
    sparse_ranked: list[tuple[UUID, float]],
) -> dict[UUID, float]:
    scores: dict[UUID, float] = {}
    for entity_id, score in dense_ranked:
        scores[entity_id] = scores.get(entity_id, 0.0) + log1p(max(score, 0.0))
    for entity_id, score in sparse_ranked:
        scores[entity_id] = scores.get(entity_id, 0.0) + log1p(max(score, 0.0))
    return scores


def fuse_hybrid_results(
    dense_ranked: list[tuple[UUID, float]],
    sparse_ranked: list[tuple[UUID, float]],
    *,
    strategy: FusionStrategy = "rrf",
    rrf_k: int = 60,
) -> list[tuple[UUID, float]]:
    if strategy == "dbsf":
        fused = distribution_based_score_fusion(dense_ranked, sparse_ranked)
    else:
        fused = reciprocal_rank_fusion(dense_ranked, sparse_ranked, k=rrf_k)
    return sorted(fused.items(), key=lambda item: item[1], reverse=True)


def apply_business_rerank(
    hits: list[HybridSearchHit],
    *,
    in_stock_boost: float = 0.05,
    primary_media_boost: float = 0.1,
) -> list[HybridSearchHit]:
    reranked: list[tuple[float, HybridSearchHit]] = []
    for hit in hits:
        boost = 0.0
        if hit.payload.get("has_stock"):
            boost += in_stock_boost
        if hit.payload.get("is_primary_media"):
            boost += primary_media_boost
        if hit.payload.get("status") == "active":
            boost += 0.02
        reranked.append((hit.fused_score + boost, hit))
    reranked.sort(key=lambda item: item[0], reverse=True)
    return [
        HybridSearchHit(
            entity_id=hit.entity_id,
            dense_score=hit.dense_score,
            sparse_score=hit.sparse_score,
            fused_score=score,
            payload=hit.payload,
            rank_dense=hit.rank_dense,
            rank_sparse=hit.rank_sparse,
        )
        for score, hit in reranked
    ]
