"""
Rebuild Chroma collections from SQLite.

Required after changing EMBED_MODEL, CHUNK_SIZE/OVERLAP, or collection version:

    python -m common.reindex
"""

from __future__ import annotations

from common.config import CHROMA_COLLECTION, EMBED_MODEL, STORY_CHROMA_COLLECTION
from common.db import (
    fetch_all_news,
    fetch_cluster_articles,
    fetch_clusters_with_descriptions,
    fetch_clusters_without_descriptions,
    init_db,
    update_cluster_description,
)
from common.indexing import (
    delete_collection,
    delete_story_index,
    index_article,
    index_story,
    reset_index_cache,
)
from preprocessing.describe import describe_cluster


def backfill_story_descriptions() -> int:
    """Generate descriptions for clusters missing one. Returns count updated."""
    missing = fetch_clusters_without_descriptions()
    if not missing:
        return 0

    updated = 0
    for cluster_id in missing:
        member_articles = fetch_cluster_articles(cluster_id)
        description = describe_cluster(member_articles)
        update_cluster_description(cluster_id, description)
        updated += 1
        if updated % 10 == 0 or updated == len(missing):
            print(f"Backfilled descriptions: {updated}/{len(missing)}")
    return updated


def reindex_stories() -> int:
    """Rebuild story_index from SQLite cluster descriptions."""
    if delete_story_index():
        print(f"Deleted existing collection: {STORY_CHROMA_COLLECTION}")
    else:
        print(f"No existing collection to delete: {STORY_CHROMA_COLLECTION}")
    reset_index_cache()

    clusters = fetch_clusters_with_descriptions()
    if not clusters:
        print("No story descriptions in SQLite.")
        return 0

    for i, row in enumerate(clusters, start=1):
        index_story(row["cluster_id"], row["description"], row["created_at"])
        if i % 10 == 0 or i == len(clusters):
            print(f"Indexed stories: {i}/{len(clusters)}")

    print(f"Story reindex complete: {len(clusters)} stories")
    return len(clusters)


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
        print("No articles in SQLite; empty collection will be created on first index.")

    backfilled = backfill_story_descriptions()
    if backfilled:
        print(f"Backfilled {backfilled} missing story descriptions")

    reindex_stories()

    print(
        f"Reindex complete with model {EMBED_MODEL}: "
        f"{total_articles} articles, {total_chunks} chunks"
    )
    return total_chunks


if __name__ == "__main__":
    reindex()
