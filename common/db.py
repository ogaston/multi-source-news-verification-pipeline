import hashlib
import sqlite3
from datetime import datetime

from common.config import DB_NAME, PREPROCESS_BATCH_SIZE
from common.indexing import index_article


def init_db():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS raw_articles (
            id TEXT PRIMARY KEY,
            url TEXT UNIQUE,
            source TEXT,
            title TEXT,
            content TEXT,
            date TEXT,
            author TEXT,
            category TEXT,
            scraped_at TEXT,
            processed INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS topic_clusters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cluster_id TEXT NOT NULL,
            article_id TEXT NOT NULL,
            description TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(cluster_id, article_id)
        )
    """)
    conn.close()


def url_exists(url: str) -> bool:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM raw_articles WHERE url = ?", (url,))
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
            f"SELECT url FROM raw_articles WHERE url IN ({placeholders})",
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
    INSERT INTO raw_articles (
        id, url, source, title, content, date, author, category, scraped_at, processed
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
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

    index_article(
        {
            "id": news_id,
            "url": url,
            "source": source,
            "title": title,
            "content": content,
            "date": date,
        }
    )

    return news_id


def fetch_all_news() -> list[dict]:
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, url, source, title, content, date FROM raw_articles"
        ).fetchall()
        return [dict(row) for row in rows]


def fetch_unprocessed_articles(
    limit: int = PREPROCESS_BATCH_SIZE,
) -> list[dict]:
    """Return up to `limit` articles with processed=0, oldest scraped first."""
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT id, url, source, title, content, date, scraped_at
            FROM raw_articles
            WHERE processed = 0
            ORDER BY scraped_at ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]


def mark_articles_processed(ids: list[str]) -> None:
    if not ids:
        return
    with sqlite3.connect(DB_NAME) as conn:
        placeholders = ",".join("?" * len(ids))
        conn.execute(
            f"UPDATE raw_articles SET processed = 1 WHERE id IN ({placeholders})",
            ids,
        )
        conn.commit()


def insert_topic_cluster_rows(
    rows: list[tuple[str, str, str | None, str]],
) -> None:
    """
    Insert topic cluster memberships.
    Each row is (cluster_id, article_id, description, created_at).
    """
    if not rows:
        return
    with sqlite3.connect(DB_NAME) as conn:
        conn.executemany(
            """
            INSERT OR IGNORE INTO topic_clusters
                (cluster_id, article_id, description, created_at)
            VALUES (?, ?, ?, ?)
            """,
            rows,
        )
        conn.commit()
