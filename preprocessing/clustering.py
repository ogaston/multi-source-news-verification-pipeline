"""Agglomerative hierarchical clustering over article embeddings."""

from __future__ import annotations

from collections import defaultdict
from uuid import uuid4

import numpy as np
from sklearn.cluster import AgglomerativeClustering

from common.config import CLUSTER_DISTANCE_THRESHOLD


def article_document_text(title: str | None, content: str | None) -> str:
    parts = [(title or "").strip(), (content or "").strip()]
    return "\n\n".join(p for p in parts if p)


def l2_normalize(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    return matrix / norms


def cluster_embeddings(
    article_ids: list[str],
    embeddings: list[list[float]] | np.ndarray,
    *,
    distance_threshold: float = CLUSTER_DISTANCE_THRESHOLD,
) -> dict[str, list[str]]:
    """
    Cluster article embeddings with average-linkage AHC (cosine distance).

    Returns mapping of cluster_id (UUID) -> list of article_ids.
    """
    if not article_ids:
        return {}
    if len(article_ids) != len(embeddings):
        raise ValueError("article_ids and embeddings must have the same length")

    if len(article_ids) == 1:
        return {str(uuid4()): [article_ids[0]]}

    matrix = l2_normalize(np.asarray(embeddings, dtype=np.float64))
    model = AgglomerativeClustering(
        n_clusters=None,
        metric="cosine",
        linkage="average",
        distance_threshold=distance_threshold,
    )
    labels = model.fit_predict(matrix)

    grouped: dict[int, list[str]] = defaultdict(list)
    for article_id, label in zip(article_ids, labels, strict=True):
        grouped[int(label)].append(article_id)

    return {str(uuid4()): members for members in grouped.values()}
