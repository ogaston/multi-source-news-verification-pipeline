"""
Rebuild Chroma collections from the database.

Required after changing EMBED_MODEL, CHUNK_SIZE/OVERLAP, or collection version:

    python -m common.reindex
"""

from __future__ import annotations

from common.config import (
    CHROMA_COLLECTION,
    EMBED_MODEL,
    STORY_CHROMA_COLLECTION,
    VERIFIED_CHROMA_COLLECTION,
)
from common.db import (
    fetch_all_news,
    fetch_all_verified_articles,
    fetch_cluster_articles,
    fetch_clusters_with_descriptions,
    fetch_clusters_without_descriptions,
    init_db,
    update_cluster_metadata,
)
from common.indexing import (
    delete_collection,
    delete_story_index,
    delete_verified_index,
    index_article,
    index_story,
    index_verified_article,
    reset_index_cache,
)
from preprocessing.describe import describe_cluster


def backfill_story_descriptions() -> int:
    """Generate descriptions for clusters missing one. Returns count updated."""
    missing = fetch_clusters_without_descriptions()
    if not missing:
        print("[reindex] no clusters missing descriptions", flush=True)
        return 0

    print(f"[reindex] backfilling {len(missing)} cluster descriptions...", flush=True)
    updated = 0
    for cluster_id in missing:
        updated += 1
        print(
            f"[reindex] describe {updated}/{len(missing)} "
            f"cluster={cluster_id[:8]}…",
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
        print(
            f"[reindex]   -> {meta['category']} / {meta['place']}: "
            f"{meta['description'][:100]}",
            flush=True,
        )
    print(f"[reindex] backfill complete: {updated}/{len(missing)}", flush=True)
    return updated


def reindex_stories() -> int:
    """Rebuild story_index from cluster descriptions."""
    if delete_story_index():
        print(f"Deleted existing collection: {STORY_CHROMA_COLLECTION}")
    else:
        print(f"No existing collection to delete: {STORY_CHROMA_COLLECTION}")
    reset_index_cache()

    clusters = fetch_clusters_with_descriptions()
    if not clusters:
        print("No story descriptions in database.")
        return 0

    for i, row in enumerate(clusters, start=1):
        index_story(row["cluster_id"], row["description"], row["created_at"])
        if i % 10 == 0 or i == len(clusters):
            print(f"Indexed stories: {i}/{len(clusters)}")

    print(f"Story reindex complete: {len(clusters)} stories")
    return len(clusters)


def reindex_verified() -> int:
    """Rebuild verified_index from verified_articles."""
    if delete_verified_index():
        print(f"Deleted existing collection: {VERIFIED_CHROMA_COLLECTION}")
    else:
        print(f"No existing collection to delete: {VERIFIED_CHROMA_COLLECTION}")
    reset_index_cache()

    articles = fetch_all_verified_articles()
    if not articles:
        print("No verified articles in database.")
        return 0

    for i, row in enumerate(articles, start=1):
        index_verified_article(
            cluster_id=row["cluster_id"],
            title=row.get("title") or "",
            content=row.get("content") or "",
            date=row.get("date"),
            status=row.get("status") or "draft",
        )
        if i % 10 == 0 or i == len(articles):
            print(f"Indexed verified articles: {i}/{len(articles)}")

    print(f"Verified reindex complete: {len(articles)} articles")
    return len(articles)


def reindex() -> int:
    init_db()
    articles = fetch_all_news()

    if delete_collection():
        print(f"Deleted existing collection: {CHROMA_COLLECTION}")
    else:
        print(f"No existing collection to delete: {CHROMA_COLLECTION}")
    reset_index_cache()

    total_articles = 0
    total_chunks = 0
    if articles:
        for row in articles:
            n = index_article(row)
            total_articles += 1
            total_chunks += n
            if total_articles % 10 == 0 or total_articles == len(articles):
                print(
                    f"Indexed {total_articles}/{len(articles)} articles "
                    f"({total_chunks} chunks)"
                )
    else:
        print("No articles in database; empty collection will be created on first index.")

    backfilled = backfill_story_descriptions()
    if backfilled:
        print(f"Backfilled {backfilled} missing story descriptions")

    reindex_stories()
    reindex_verified()

    print(
        f"Reindex complete with model {EMBED_MODEL}: "
        f"{total_articles} articles, {total_chunks} chunks"
    )
    return total_chunks


if __name__ == "__main__":
    reindex()
