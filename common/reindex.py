"""
Rebuild the Chroma collection from SQLite using the current embedding model.

Required after changing EMBED_MODEL (old vectors are incompatible):

    python -m common.reindex
"""

from __future__ import annotations

import chromadb
from chromadb.utils import embedding_functions

from common.config import CHROMA_COLLECTION, CHROMA_PATH, EMBED_MODEL
from common.db import fetch_all_news, init_db


def reindex() -> int:
    init_db()
    articles = fetch_all_news()

    client = chromadb.PersistentClient(path=CHROMA_PATH)
    try:
        client.delete_collection(CHROMA_COLLECTION)
        print(f"Deleted existing collection: {CHROMA_COLLECTION}")
    except Exception:
        print(f"No existing collection to delete: {CHROMA_COLLECTION}")

    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBED_MODEL
    )
    collection = client.get_or_create_collection(
        name=CHROMA_COLLECTION, embedding_function=ef
    )

    if not articles:
        print("No articles in SQLite; empty collection created.")
        return 0

    batch_size = 64
    total = 0
    for i in range(0, len(articles), batch_size):
        batch = articles[i : i + batch_size]
        collection.upsert(
            ids=[row["id"] for row in batch],
            documents=[f"{row['title']}\n\n{row['content']}" for row in batch],
            metadatas=[
                {
                    "url": row["url"] or "",
                    "source": row["source"] or "",
                    "title": row["title"] or "",
                    "date": row["date"] or "",
                }
                for row in batch
            ],
        )
        total += len(batch)
        print(f"Indexed {total}/{len(articles)}")

    print(f"Reindex complete with model {EMBED_MODEL}: {total} articles")
    return total


if __name__ == "__main__":
    reindex()
