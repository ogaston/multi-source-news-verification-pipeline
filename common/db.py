import hashlib
import sqlite3
from datetime import datetime

from common.config import DB_NAME, PREPROCESS_BATCH_SIZE
from common.indexing import index_article


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {row[1] for row in rows}


def _migrate_topic_clusters_drop_description(conn: sqlite3.Connection) -> None:
    """Rebuild topic_clusters without description if an older schema is present."""
    columns = _table_columns(conn, "topic_clusters")
    if not columns or "description" not in columns:
        return
    conn.execute("""
        CREATE TABLE topic_clusters_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cluster_id TEXT NOT NULL,
            article_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(cluster_id, article_id)
        )
    """)
    conn.execute("""
        INSERT INTO topic_clusters_new (cluster_id, article_id, created_at)
        SELECT cluster_id, article_id, created_at FROM topic_clusters
    """)
    conn.execute("DROP TABLE topic_clusters")
    conn.execute("ALTER TABLE topic_clusters_new RENAME TO topic_clusters")


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
            created_at TEXT NOT NULL,
            UNIQUE(cluster_id, article_id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS clusters (
            cluster_id TEXT PRIMARY KEY,
            description TEXT,
            created_at TEXT NOT NULL
        )
    """)
    _migrate_topic_clusters_drop_description(conn)
    conn.commit()
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
    rows: list[tuple[str, str, str]],
) -> None:
    """
    Insert topic cluster memberships.
    Each row is (cluster_id, article_id, created_at).
    """
    if not rows:
        return
    with sqlite3.connect(DB_NAME) as conn:
        conn.executemany(
            """
            INSERT OR IGNORE INTO topic_clusters
                (cluster_id, article_id, created_at)
            VALUES (?, ?, ?)
            """,
            rows,
        )
        conn.commit()


def insert_clusters(
    rows: list[tuple[str, str | None, str]],
) -> None:
    """
    Insert cluster metadata rows.
    Each row is (cluster_id, description, created_at).
    """
    if not rows:
        return
    with sqlite3.connect(DB_NAME) as conn:
        conn.executemany(
            """
            INSERT OR IGNORE INTO clusters
                (cluster_id, description, created_at)
            VALUES (?, ?, ?)
            """,
            rows,
        )
        conn.commit()


def update_cluster_description(cluster_id: str, description: str) -> None:
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute(
            "UPDATE clusters SET description = ? WHERE cluster_id = ?",
            (description, cluster_id),
        )
        conn.commit()


def fetch_cluster_articles(cluster_id: str) -> list[dict]:
    """Return member articles (title/content/source/date) for a cluster."""
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT a.id, a.url, a.source, a.title, a.content, a.date
            FROM topic_clusters tc
            JOIN raw_articles a ON a.id = tc.article_id
            WHERE tc.cluster_id = ?
            ORDER BY a.date ASC
            """,
            (cluster_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def fetch_clusters_with_descriptions() -> list[dict]:
    """Return clusters that have a non-null description."""
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT cluster_id, description, created_at
            FROM clusters
            WHERE description IS NOT NULL AND TRIM(description) != ''
            ORDER BY created_at ASC
            """
        ).fetchall()
        return [dict(row) for row in rows]


def fetch_clusters_without_descriptions() -> list[str]:
    """Return cluster_ids missing a description."""
    with sqlite3.connect(DB_NAME) as conn:
        rows = conn.execute(
            """
            SELECT cluster_id
            FROM clusters
            WHERE description IS NULL OR TRIM(description) = ''
            ORDER BY created_at ASC
            """
        ).fetchall()
        return [row[0] for row in rows]
