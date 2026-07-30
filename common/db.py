import hashlib
import sqlite3
from datetime import datetime

from common.config import DB_NAME, PREPROCESS_BATCH_SIZE
from common.indexing import index_article


def article_fingerprint(source: str | None, title: str, date: str) -> str:
    """
    Stable dedup key: sha256 of calendar day + source + normalized title.
    Expects `date` as UTC ISO-8601 (YYYY-MM-DD...).
    """
    day = str(date)[:10]
    norm_title = " ".join((title or "").casefold().split())
    payload = f"{day}|{source or ''}|{norm_title}"
    return hashlib.sha256(payload.encode()).hexdigest()


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


def _migrate_raw_articles_article_key(conn: sqlite3.Connection) -> None:
    """Add article_key column, backfill earliest rows per fingerprint, unique index."""
    columns = _table_columns(conn, "raw_articles")
    if not columns:
        return
    if "article_key" not in columns:
        conn.execute("ALTER TABLE raw_articles ADD COLUMN article_key TEXT")

    rows = conn.execute(
        """
        SELECT id, source, title, date, scraped_at
        FROM raw_articles
        WHERE article_key IS NULL
          AND date IS NOT NULL
          AND title IS NOT NULL
        ORDER BY scraped_at ASC, id ASC
        """
    ).fetchall()

    seen_keys: set[str] = set()
    # Existing non-null keys count as taken (partial re-runs).
    for (existing_key,) in conn.execute(
        "SELECT article_key FROM raw_articles WHERE article_key IS NOT NULL"
    ):
        seen_keys.add(existing_key)

    for row_id, source, title, date, _scraped_at in rows:
        key = article_fingerprint(source, title, date)
        if key in seen_keys:
            # Collision: keep earliest row's key; leave this row NULL.
            continue
        conn.execute(
            "UPDATE raw_articles SET article_key = ? WHERE id = ?",
            (key, row_id),
        )
        seen_keys.add(key)

    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_raw_articles_article_key
        ON raw_articles(article_key)
        WHERE article_key IS NOT NULL
        """
    )


def _migrate_clusters_processed(conn: sqlite3.Connection) -> None:
    """Add clusters.processed if an older schema is present."""
    columns = _table_columns(conn, "clusters")
    if not columns or "processed" in columns:
        return
    conn.execute(
        "ALTER TABLE clusters ADD COLUMN processed INTEGER NOT NULL DEFAULT 0"
    )


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
            processed INTEGER NOT NULL DEFAULT 0,
            article_key TEXT
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
            created_at TEXT NOT NULL,
            processed INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS verified_articles (
            id TEXT PRIMARY KEY,
            cluster_id TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            image_url TEXT,
            date TEXT,
            sources TEXT,
            status TEXT NOT NULL DEFAULT 'draft',
            created_at TEXT NOT NULL
        )
    """)
    _migrate_topic_clusters_drop_description(conn)
    _migrate_raw_articles_article_key(conn)
    _migrate_clusters_processed(conn)
    conn.commit()
    conn.close()


def url_exists(url: str) -> bool:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM raw_articles WHERE url = ?", (url,))
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0


def article_key_exists(key: str) -> bool:
    """Return True if an article with this fingerprint is already stored."""
    if not key:
        return False
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM raw_articles WHERE article_key = ? LIMIT 1",
        (key,),
    )
    found = cursor.fetchone() is not None
    conn.close()
    return found


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


def save_news(news: dict) -> str | None:
    """
    Persist article to SQLite and Chroma.
    Returns news id, or None if skipped due to article_key collision on a new URL.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    news_id = hashlib.sha256(news["url"].encode()).hexdigest()
    scraped_at = datetime.now().isoformat()
    title = news["title"]
    content = news["content"]
    source = news.get("source")
    date = news["date"]
    url = news["url"]
    key = article_fingerprint(source, title, date)

    # Different URL, same fingerprint → skip (do not overwrite existing row).
    cursor.execute(
        "SELECT id, url FROM raw_articles WHERE article_key = ? LIMIT 1",
        (key,),
    )
    existing = cursor.fetchone()
    if existing is not None and existing[1] != url:
        conn.close()
        return None

    cursor.execute(
        """
    INSERT INTO raw_articles (
        id, url, source, title, content, date, author, category,
        scraped_at, processed, article_key
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
    ON CONFLICT(url) DO UPDATE SET
        source = excluded.source,
        title = excluded.title,
        content = excluded.content,
        date = excluded.date,
        author = excluded.author,
        category = excluded.category,
        scraped_at = excluded.scraped_at,
        article_key = excluded.article_key
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
            key,
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
    New rows default to processed=0.
    """
    if not rows:
        return
    with sqlite3.connect(DB_NAME) as conn:
        conn.executemany(
            """
            INSERT OR IGNORE INTO clusters
                (cluster_id, description, created_at, processed)
            VALUES (?, ?, ?, 0)
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


def fetch_cluster(cluster_id: str) -> dict | None:
    """Return one cluster row, or None if missing."""
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT cluster_id, description, created_at, processed
            FROM clusters
            WHERE cluster_id = ?
            """,
            (cluster_id,),
        ).fetchone()
        return dict(row) if row else None


def fetch_unprocessed_clusters(limit: int) -> list[dict]:
    """
    Return up to `limit` clusters with processed=0 that have a description.
    Oldest created_at first.
    """
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT cluster_id, description, created_at, processed
            FROM clusters
            WHERE processed = 0
              AND description IS NOT NULL
              AND TRIM(description) != ''
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]


def mark_cluster_processed(cluster_id: str) -> None:
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute(
            "UPDATE clusters SET processed = 1 WHERE cluster_id = ?",
            (cluster_id,),
        )
        conn.commit()


def insert_verified_article(
    *,
    cluster_id: str,
    title: str,
    content: str,
    image_url: str | None = None,
    date: str | None = None,
    sources: str | None = None,
    status: str = "draft",
) -> str:
    """
    Upsert a verified article for cluster_id.
    Returns the article id. Does not overwrite created_at on conflict.
    """
    article_id = hashlib.sha256(f"verified:{cluster_id}".encode()).hexdigest()
    created_at = datetime.now().isoformat()
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute(
            """
            INSERT INTO verified_articles (
                id, cluster_id, title, content, image_url, date, sources, status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(cluster_id) DO UPDATE SET
                title = excluded.title,
                content = excluded.content,
                image_url = excluded.image_url,
                date = excluded.date,
                sources = excluded.sources,
                status = excluded.status
            """,
            (
                article_id,
                cluster_id,
                title,
                content,
                image_url,
                date,
                sources,
                status,
                created_at,
            ),
        )
        conn.commit()
    return article_id


def fetch_verified_article(cluster_id: str) -> dict | None:
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT id, cluster_id, title, content, image_url, date, sources, status, created_at
            FROM verified_articles
            WHERE cluster_id = ?
            """,
            (cluster_id,),
        ).fetchone()
        return dict(row) if row else None


def fetch_recent_clusters(
    date_threshold: str,
    *,
    source: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """
    Clusters with at least one member article on/after date_threshold.

    Optional source keeps clusters that have any matching outlet article
    in the window. Ordered by total member count DESC, then newest member date.
    """
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        if source:
            rows = conn.execute(
                """
                SELECT
                    c.cluster_id,
                    c.description,
                    c.created_at,
                    COUNT(a_all.id) AS article_count,
                    MAX(a_all.date) AS latest_date
                FROM clusters c
                JOIN topic_clusters tc_all
                    ON tc_all.cluster_id = c.cluster_id
                JOIN raw_articles a_all
                    ON a_all.id = tc_all.article_id
                WHERE c.cluster_id IN (
                    SELECT DISTINCT tc.cluster_id
                    FROM topic_clusters tc
                    JOIN raw_articles a ON a.id = tc.article_id
                    WHERE a.date >= ?
                      AND a.source = ?
                )
                GROUP BY c.cluster_id, c.description, c.created_at
                ORDER BY article_count DESC, latest_date DESC
                LIMIT ?
                """,
                (date_threshold, source, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT
                    c.cluster_id,
                    c.description,
                    c.created_at,
                    COUNT(a_all.id) AS article_count,
                    MAX(a_all.date) AS latest_date
                FROM clusters c
                JOIN topic_clusters tc_all
                    ON tc_all.cluster_id = c.cluster_id
                JOIN raw_articles a_all
                    ON a_all.id = tc_all.article_id
                WHERE c.cluster_id IN (
                    SELECT DISTINCT tc.cluster_id
                    FROM topic_clusters tc
                    JOIN raw_articles a ON a.id = tc.article_id
                    WHERE a.date >= ?
                )
                GROUP BY c.cluster_id, c.description, c.created_at
                ORDER BY article_count DESC, latest_date DESC
                LIMIT ?
                """,
                (date_threshold, limit),
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
