import hashlib
import sqlite3
from datetime import datetime

import chromadb
from chromadb.utils import embedding_functions

from common.config import CHROMA_COLLECTION, CHROMA_PATH, DB_NAME, EMBED_MODEL

_vector_collection = None


def _get_vector_collection():
    global _vector_collection
    if _vector_collection is None:
        chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
        sentence_transformer_ef = (
            embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=EMBED_MODEL
            )
        )
        _vector_collection = chroma_client.get_or_create_collection(
            name=CHROMA_COLLECTION, embedding_function=sentence_transformer_ef
        )
    return _vector_collection


def init_db():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS news (
            id TEXT PRIMARY KEY,
            url TEXT UNIQUE,
            source TEXT,
            title TEXT,
            content TEXT,
            date TEXT,
            author TEXT,
            category TEXT,
            scraped_at TEXT
        )
    """)
    conn.close()


def url_exists(url: str) -> bool:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM news WHERE url = ?", (url,))
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0


def existing_urls(urls: list[str]) -> set[str]:
    """Return the subset of urls already stored in SQLite."""
    if not urls:
        return set()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    known: set[str] = set()
    # SQLite default max variable count is 999; chunk to stay under it.
    chunk_size = 900
    for i in range(0, len(urls), chunk_size):
        chunk = urls[i : i + chunk_size]
        placeholders = ",".join("?" * len(chunk))
        cursor.execute(
            f"SELECT url FROM news WHERE url IN ({placeholders})",
            chunk,
        )
        known.update(row[0] for row in cursor.fetchall())
    conn.close()
    return known


def save_news(news: dict) -> str:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    news_id = hashlib.sha256(news["url"].encode()).hexdigest()
    scraped_at = datetime.now().isoformat()
    title = news["title"]
    content = news["content"]
    source = news.get("source")
    date = news["date"]
    url = news["url"]

    cursor.execute(
        """
    INSERT INTO news (id, url, source, title, content, date, author, category, scraped_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(url) DO UPDATE SET
        source = excluded.source,
        title = excluded.title,
        content = excluded.content,
        date = excluded.date,
        author = excluded.author,
        category = excluded.category,
        scraped_at = excluded.scraped_at
    """,
        (
            news_id,
            url,
            source,
            title,
            content,
            date,
            news["author"],
            news["category"],
            scraped_at,
        ),
    )
    conn.commit()
    conn.close()

    collection = _get_vector_collection()
    collection.upsert(
        ids=[news_id],
        documents=[f"{title}\n\n{content}"],
        metadatas=[
            {
                "url": url,
                "source": source or "",
                "title": title or "",
                "date": date or "",
            }
        ],
    )

    return news_id


def fetch_all_news() -> list[dict]:
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, url, source, title, content, date FROM news"
        ).fetchall()
        return [dict(row) for row in rows]
