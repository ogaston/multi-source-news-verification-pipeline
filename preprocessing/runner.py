"""
Preprocess unprocessed raw_articles into topic_clusters via embedding AHC.

    python -m preprocessing.runner
"""

from __future__ import annotations

from datetime import datetime, timezone

from common.config import (
    CLUSTER_DISTANCE_THRESHOLD,
    PREPROCESS_BATCH_SIZE,
    PREPROCESS_CLUSTER_LIMIT,
)
from common.db import (
    fetch_cluster_articles,
    fetch_unprocessed_articles,
    init_db,
    insert_clusters,
    insert_topic_cluster_rows,
    mark_articles_processed,
    update_cluster_metadata,
)
from common.indexing import embed_texts, index_story
from preprocessing.clustering import article_document_text, cluster_embeddings
from preprocessing.describe import describe_cluster


def run_preprocess(
    *,
    limit: int = PREPROCESS_BATCH_SIZE,
    cluster_limit: int = PREPROCESS_CLUSTER_LIMIT,
    distance_threshold: float = CLUSTER_DISTANCE_THRESHOLD,
) -> int:
    """
    Cluster up to `limit` unprocessed articles and mark them processed.

    When `cluster_limit` > 0, only the largest that many clusters are
    described/indexed; the rest stay in DB for later backfill.
    Returns number of articles processed.
    """
    init_db()
    print(f"[preprocess] fetching up to {limit} unprocessed articles...", flush=True)
    articles = fetch_unprocessed_articles(limit=limit)
    if not articles:
        print("[preprocess] no unprocessed articles to cluster.", flush=True)
        return 0

    article_ids = [a["id"] for a in articles]
    texts = [
        article_document_text(a.get("title"), a.get("content")) for a in articles
    ]
    print(f"[preprocess] embedding {len(texts)} articles...", flush=True)
    embeddings = embed_texts(texts)

    print(
        f"[preprocess] clustering (distance_threshold={distance_threshold})...",
        flush=True,
    )
    clusters = cluster_embeddings(
        article_ids,
        embeddings,
        distance_threshold=distance_threshold,
    )
    print(f"[preprocess] formed {len(clusters)} clusters", flush=True)

    created_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    membership_rows: list[tuple[str, str, str]] = []
    cluster_rows: list[tuple[str, str | None, str]] = []
    for cluster_id, members in clusters.items():
        cluster_rows.append((cluster_id, None, created_at))
        for article_id in members:
            membership_rows.append((cluster_id, article_id, created_at))

    print("[preprocess] writing cluster membership to DB...", flush=True)
    insert_topic_cluster_rows(membership_rows)
    insert_clusters(cluster_rows)

    # Prefer largest clusters when a describe budget is set.
    ranked = sorted(
        clusters.items(),
        key=lambda item: (-len(item[1]), item[0]),
    )
    if cluster_limit > 0:
        to_describe = ranked[:cluster_limit]
        skipped = len(ranked) - len(to_describe)
        print(
            f"[preprocess] describing up to {cluster_limit} largest cluster(s) "
            f"({skipped} deferred)",
            flush=True,
        )
    else:
        to_describe = ranked

    total = len(to_describe)
    described = 0
    for cluster_id, members in to_describe:
        described += 1
        print(
            f"[preprocess] describe {described}/{total} "
            f"cluster={cluster_id[:8]}… members={len(members)}",
            flush=True,
        )
        member_articles = fetch_cluster_articles(cluster_id)
        meta = describe_cluster(member_articles)
        update_cluster_metadata(
            cluster_id,
            description=meta["description"],
            category=meta["category"],
            place=meta["place"],
        )
        index_story(cluster_id, meta["description"], created_at)
        print(
            f"[preprocess]   -> {meta['category']} / {meta['place']}: "
            f"{meta['description'][:100]}",
            flush=True,
        )

    print("[preprocess] marking articles processed...", flush=True)
    mark_articles_processed(article_ids)

    print(
        f"[preprocess] complete: {len(article_ids)} articles -> "
        f"{len(clusters)} clusters ({described} described)",
        flush=True,
    )
    return len(article_ids)


def main() -> None:
    run_preprocess()


if __name__ == "__main__":
    main()
