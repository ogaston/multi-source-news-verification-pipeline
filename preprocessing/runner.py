"""
Preprocess unprocessed raw_articles into topic_clusters via embedding AHC.

    python -m preprocessing.runner
"""

from __future__ import annotations

from datetime import datetime, timezone

from common.config import CLUSTER_DISTANCE_THRESHOLD, PREPROCESS_BATCH_SIZE
from common.db import (
    fetch_unprocessed_articles,
    init_db,
    insert_topic_cluster_rows,
    mark_articles_processed,
)
from common.indexing import embed_texts
from preprocessing.clustering import article_document_text, cluster_embeddings


def run_preprocess(
    *,
    limit: int = PREPROCESS_BATCH_SIZE,
    distance_threshold: float = CLUSTER_DISTANCE_THRESHOLD,
) -> int:
    """
    Cluster up to `limit` unprocessed articles and mark them processed.
    Returns number of articles processed.
    """
    init_db()
    articles = fetch_unprocessed_articles(limit=limit)
    if not articles:
        print("No unprocessed articles to cluster.")
        return 0

    article_ids = [a["id"] for a in articles]
    texts = [
        article_document_text(a.get("title"), a.get("content")) for a in articles
    ]
    print(f"Embedding {len(texts)} articles for clustering...")
    embeddings = embed_texts(texts)

    clusters = cluster_embeddings(
        article_ids,
        embeddings,
        distance_threshold=distance_threshold,
    )
    created_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    rows: list[tuple[str, str, str | None, str]] = []
    for cluster_id, members in clusters.items():
        for article_id in members:
            rows.append((cluster_id, article_id, None, created_at))

    insert_topic_cluster_rows(rows)
    mark_articles_processed(article_ids)

    print(
        f"Preprocess complete: {len(article_ids)} articles -> "
        f"{len(clusters)} clusters"
    )
    return len(article_ids)


def main() -> None:
    run_preprocess()


if __name__ == "__main__":
    main()
