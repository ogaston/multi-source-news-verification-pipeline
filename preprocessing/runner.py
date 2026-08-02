"""
Preprocess unprocessed raw_articles into topic_clusters via embedding AHC.

Daily default: previous local calendar day (PIPELINE_TZ).

    python -m preprocessing.runner
    python -m preprocessing.runner --date 2026-07-31
    python -m preprocessing.runner --no-day-filter
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timezone

from common.config import (
    CLUSTER_DISTANCE_THRESHOLD,
    PIPELINE_TZ,
    PREPROCESS_BATCH_SIZE,
    PREPROCESS_CLUSTER_LIMIT,
    PREPROCESS_DAY_OFFSET,
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
from common.pipeline_time import local_day_bounds, resolve_preprocess_day
from preprocessing.clustering import article_document_text, cluster_embeddings
from preprocessing.describe import describe_cluster


def run_preprocess(
    *,
    limit: int = PREPROCESS_BATCH_SIZE,
    cluster_limit: int = PREPROCESS_CLUSTER_LIMIT,
    distance_threshold: float = CLUSTER_DISTANCE_THRESHOLD,
    day: date | None = None,
    day_offset: int = PREPROCESS_DAY_OFFSET,
    no_day_filter: bool = False,
) -> int:
    """
    Cluster up to `limit` unprocessed articles and mark them processed.

    By default only articles scraped on the previous local calendar day
    (PIPELINE_TZ) are eligible. Pass `day` for an explicit local day, or
    `no_day_filter=True` to ignore the day window (backfill). When
    `cluster_limit` > 0, only the largest that many clusters are
    described/indexed; the rest stay in DB for later backfill.
    Returns number of articles processed.
    """
    init_db()
    day_start: str | None = None
    day_end: str | None = None
    if not no_day_filter:
        target_day = resolve_preprocess_day(explicit_date=day, day_offset=day_offset)
        day_start, day_end = local_day_bounds(target_day)
        print(
            f"[preprocess] fetching up to {limit} unprocessed articles "
            f"(local_day={target_day.isoformat()} tz={PIPELINE_TZ} "
            f"window=[{day_start}, {day_end}))...",
            flush=True,
        )
    else:
        print(
            f"[preprocess] fetching up to {limit} unprocessed articles "
            f"(no day filter)...",
            flush=True,
        )

    articles = fetch_unprocessed_articles(
        limit=limit,
        day_start=day_start,
        day_end=day_end,
    )
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Cluster unprocessed raw articles for one local calendar day "
            f"(default: previous day in {PIPELINE_TZ})."
        )
    )
    parser.add_argument(
        "--date",
        type=date.fromisoformat,
        default=None,
        help="Local calendar day to process (YYYY-MM-DD). Overrides day offset.",
    )
    parser.add_argument(
        "--no-day-filter",
        action="store_true",
        help="Ignore the calendar-day window (backfill older unprocessed).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=PREPROCESS_BATCH_SIZE,
        help=f"Max articles to cluster (default: {PREPROCESS_BATCH_SIZE})",
    )
    parser.add_argument(
        "--cluster-limit",
        type=int,
        default=PREPROCESS_CLUSTER_LIMIT,
        help=f"Max clusters to describe (default: {PREPROCESS_CLUSTER_LIMIT})",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_preprocess(
        limit=max(1, args.limit),
        cluster_limit=args.cluster_limit,
        day=args.date,
        no_day_filter=args.no_day_filter,
    )


if __name__ == "__main__":
    main()
