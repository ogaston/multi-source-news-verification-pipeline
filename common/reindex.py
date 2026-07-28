"""
Rebuild the Chroma collection from SQLite using chunked LlamaIndex nodes.

Required after changing EMBED_MODEL, CHUNK_SIZE/OVERLAP, or collection version:

    python -m common.reindex
"""

from __future__ import annotations

from common.config import CHROMA_COLLECTION, EMBED_MODEL
from common.db import fetch_all_news, init_db
from common.indexing import delete_collection, index_article, reset_index_cache


def reindex() -> int:
    init_db()
    articles = fetch_all_news()

    if delete_collection():
        print(f"Deleted existing collection: {CHROMA_COLLECTION}")
    else:
        print(f"No existing collection to delete: {CHROMA_COLLECTION}")
    reset_index_cache()

    if not articles:
        print("No articles in SQLite; empty collection will be created on first index.")
        return 0

    total_articles = 0
    total_chunks = 0
    for row in articles:
        n = index_article(row)
        total_articles += 1
        total_chunks += n
        if total_articles % 10 == 0 or total_articles == len(articles):
            print(
                f"Indexed {total_articles}/{len(articles)} articles "
                f"({total_chunks} chunks)"
            )

    print(
        f"Reindex complete with model {EMBED_MODEL}: "
        f"{total_articles} articles, {total_chunks} chunks"
    )
    return total_chunks


if __name__ == "__main__":
    reindex()
