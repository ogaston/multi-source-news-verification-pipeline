"""PostgreSQL data access for the news pipeline (SQLAlchemy)."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from common.config import (
    DATABASE_URL,
    PREPROCESS_BATCH_SIZE,
    STORY_AUDIT_MAX_AGE_DAYS,
)
from common.pipeline_time import now_pipeline_iso
from common.taxonomy import normalize_category, normalize_place

_engine: Engine | None = None
_QMARK_RE = re.compile(r"\?")


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    return _engine


def reset_engine() -> None:
    """Dispose and clear the cached engine (used by tests)."""
    global _engine
    if _engine is not None:
        _engine.dispose()
        _engine = None


def init_db() -> None:
    """Verify database connectivity. Schema is owned by Alembic."""
    with get_engine().connect() as conn:
        conn.execute(text("SELECT 1"))


def _bind_qmark(sql: str, params: tuple[Any, ...] | list[Any]) -> tuple[str, dict[str, Any]]:
    """Convert sqlite-style `?` placeholders to SQLAlchemy named binds."""
    binds: dict[str, Any] = {}
    idx = 0

    def _repl(_match: re.Match[str]) -> str:
        nonlocal idx
        key = f"p{idx}"
        binds[key] = params[idx]
        idx += 1
        return f":{key}"

    converted = _QMARK_RE.sub(_repl, sql)
    if idx != len(params):
        raise ValueError(
            f"placeholder count ({idx}) does not match params ({len(params)})"
        )
    return converted, binds


def query_db(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    """Run a read query; returns list of dict rows."""
    converted, binds = _bind_qmark(sql, params)
    with get_engine().connect() as conn:
        result = conn.execute(text(converted), binds)
        return [dict(row._mapping) for row in result]


def article_fingerprint(source: str | None, title: str, date: str) -> str:
    """
    Stable dedup key: sha256 of calendar day + source + normalized title.
    Expects `date` as UTC ISO-8601 (YYYY-MM-DD...).
    """
    day = str(date)[:10]
    norm_title = " ".join((title or "").casefold().split())
    payload = f"{day}|{source or ''}|{norm_title}"
    return hashlib.sha256(payload.encode()).hexdigest()


def article_slug(title: str, cluster_id: str) -> str:
    """URL slug from title (ASCII-folded) + short cluster_id suffix for uniqueness."""
    normalized = unicodedata.normalize("NFKD", title or "")
    ascii_title = normalized.encode("ascii", "ignore").decode("ascii")
    base = re.sub(r"[^a-z0-9]+", "-", ascii_title.casefold()).strip("-")
    base = re.sub(r"-+", "-", base)
    if not base:
        base = "articulo"
    base = base[:80].rstrip("-")
    suffix = (cluster_id or "")[:8] or hashlib.sha256(
        (title or "").encode()
    ).hexdigest()[:8]
    return f"{base}-{suffix}"


def url_exists(url: str) -> bool:
    rows = query_db("SELECT COUNT(*) AS n FROM raw_articles WHERE url = ?", (url,))
    return int(rows[0]["n"]) > 0


def article_key_exists(key: str) -> bool:
    """Return True if an article with this fingerprint is already stored."""
    if not key:
        return False
    rows = query_db(
        "SELECT 1 AS ok FROM raw_articles WHERE article_key = ? LIMIT 1",
        (key,),
    )
    return bool(rows)


def existing_urls(urls: list[str]) -> set[str]:
    """Return the subset of urls already stored."""
    if not urls:
        return set()
    known: set[str] = set()
    chunk_size = 900
    with get_engine().connect() as conn:
        for i in range(0, len(urls), chunk_size):
            chunk = urls[i : i + chunk_size]
            placeholders = ", ".join(f":u{j}" for j in range(len(chunk)))
            binds = {f"u{j}": u for j, u in enumerate(chunk)}
            result = conn.execute(
                text(f"SELECT url FROM raw_articles WHERE url IN ({placeholders})"),
                binds,
            )
            known.update(row[0] for row in result)
    return known


def save_news(news: dict) -> str | None:
    """
    Persist article to Postgres and Chroma.
    Returns news id, or None if skipped due to article_key collision on a new URL.
    """
    news_id = hashlib.sha256(news["url"].encode()).hexdigest()
    scraped_at = now_pipeline_iso()
    title = news["title"]
    content = news["content"]
    source = news.get("source")
    date = news["date"]
    url = news["url"]
    key = article_fingerprint(source, title, date)

    with get_engine().begin() as conn:
        existing = conn.execute(
            text(
                "SELECT id, url FROM raw_articles WHERE article_key = :key LIMIT 1"
            ),
            {"key": key},
        ).fetchone()
        if existing is not None and existing[1] != url:
            return None

        conn.execute(
            text(
                """
                INSERT INTO raw_articles (
                    id, url, source, title, content, date, author, category,
                    scraped_at, processed, article_key
                )
                VALUES (
                    :id, :url, :source, :title, :content, :date, :author, :category,
                    :scraped_at, 0, :article_key
                )
                ON CONFLICT (url) DO UPDATE SET
                    source = EXCLUDED.source,
                    title = EXCLUDED.title,
                    content = EXCLUDED.content,
                    date = EXCLUDED.date,
                    author = EXCLUDED.author,
                    category = EXCLUDED.category,
                    scraped_at = EXCLUDED.scraped_at,
                    article_key = EXCLUDED.article_key
                """
            ),
            {
                "id": news_id,
                "url": url,
                "source": source,
                "title": title,
                "content": content,
                "date": date,
                "author": news["author"],
                "category": news["category"],
                "scraped_at": scraped_at,
                "article_key": key,
            },
        )

    from common.indexing import index_article

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
    return query_db(
        "SELECT id, url, source, title, content, date FROM raw_articles"
    )


def fetch_source_articles(source: str, date_threshold: str) -> list[dict]:
    """Articles from one outlet on/after date_threshold, newest first."""
    return query_db(
        """
        SELECT id, source, title, date, content, url
        FROM raw_articles
        WHERE source = ? AND date >= ?
        ORDER BY date DESC
        """,
        (source, date_threshold),
    )


def fetch_unprocessed_articles(
    limit: int = PREPROCESS_BATCH_SIZE,
    *,
    day_start: str | None = None,
    day_end: str | None = None,
    lookback_hours: int | None = None,
) -> list[dict]:
    """
    Return up to `limit` articles with processed=0, oldest scraped first.

    Prefer `day_start`/`day_end` (half-open local-day ISO bounds). Deprecated
    `lookback_hours` > 0 keeps a rolling UTC window for manual backfill. Omit
    both to disable the time filter.
    """
    if day_start is not None and day_end is not None:
        return query_db(
            """
            SELECT id, url, source, title, content, date, scraped_at
            FROM raw_articles
            WHERE processed = 0
              AND scraped_at >= ?
              AND scraped_at < ?
            ORDER BY scraped_at ASC
            LIMIT ?
            """,
            (day_start, day_end, limit),
        )
    if lookback_hours is not None and lookback_hours > 0:
        scraped_threshold = (
            datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
        ).isoformat().replace("+00:00", "Z")
        return query_db(
            """
            SELECT id, url, source, title, content, date, scraped_at
            FROM raw_articles
            WHERE processed = 0
              AND scraped_at >= ?
            ORDER BY scraped_at ASC
            LIMIT ?
            """,
            (scraped_threshold, limit),
        )
    return query_db(
        """
        SELECT id, url, source, title, content, date, scraped_at
        FROM raw_articles
        WHERE processed = 0
        ORDER BY scraped_at ASC
        LIMIT ?
        """,
        (limit,),
    )


def mark_articles_processed(ids: list[str]) -> None:
    if not ids:
        return
    placeholders = ", ".join(f":id{i}" for i in range(len(ids)))
    binds = {f"id{i}": aid for i, aid in enumerate(ids)}
    with get_engine().begin() as conn:
        conn.execute(
            text(
                f"UPDATE raw_articles SET processed = 1 WHERE id IN ({placeholders})"
            ),
            binds,
        )


def insert_topic_cluster_rows(
    rows: list[tuple[str, str, str]],
) -> None:
    """
    Insert topic cluster memberships.
    Each row is (cluster_id, article_id, created_at).
    """
    if not rows:
        return
    with get_engine().begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO topic_clusters (cluster_id, article_id, created_at)
                VALUES (:cluster_id, :article_id, :created_at)
                ON CONFLICT (cluster_id, article_id) DO NOTHING
                """
            ),
            [
                {
                    "cluster_id": cluster_id,
                    "article_id": article_id,
                    "created_at": created_at,
                }
                for cluster_id, article_id, created_at in rows
            ],
        )


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
    with get_engine().begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO clusters
                    (cluster_id, description, created_at, processed)
                VALUES (:cluster_id, :description, :created_at, 0)
                ON CONFLICT (cluster_id) DO NOTHING
                """
            ),
            [
                {
                    "cluster_id": cluster_id,
                    "description": description,
                    "created_at": created_at,
                }
                for cluster_id, description, created_at in rows
            ],
        )


def update_cluster_description(cluster_id: str, description: str) -> None:
    """Update cluster description only."""
    with get_engine().begin() as conn:
        conn.execute(
            text(
                "UPDATE clusters SET description = :description WHERE cluster_id = :cluster_id"
            ),
            {"description": description, "cluster_id": cluster_id},
        )


def update_cluster_metadata(
    cluster_id: str,
    *,
    description: str,
    category: str | None = None,
    place: str | None = None,
) -> None:
    with get_engine().begin() as conn:
        conn.execute(
            text(
                """
                UPDATE clusters
                SET description = :description,
                    category = :category,
                    place = :place
                WHERE cluster_id = :cluster_id
                """
            ),
            {
                "description": description,
                "category": normalize_category(category),
                "place": normalize_place(place),
                "cluster_id": cluster_id,
            },
        )


def fetch_cluster_articles(cluster_id: str) -> list[dict]:
    """Return member articles (title/content/source/date/category/url) for a cluster."""
    return query_db(
        """
        SELECT a.id, a.url, a.source, a.title, a.content, a.date, a.category
        FROM topic_clusters tc
        JOIN raw_articles a ON a.id = tc.article_id
        WHERE tc.cluster_id = ?
        ORDER BY a.date ASC
        """,
        (cluster_id,),
    )


def fetch_cluster(cluster_id: str) -> dict | None:
    """Return one cluster row, or None if missing."""
    rows = query_db(
        """
        SELECT cluster_id, description, category, place, created_at, processed
        FROM clusters
        WHERE cluster_id = ?
        """,
        (cluster_id,),
    )
    return rows[0] if rows else None


def fetch_unprocessed_clusters(
    limit: int,
    *,
    max_age_days: int = STORY_AUDIT_MAX_AGE_DAYS,
) -> list[dict]:
    """
    Return up to `limit` unprocessed clusters that have a description.

    Only clusters whose newest member article is within `max_age_days` of now
    are eligible. Ranked by member count, then distinct sources, then newest
    member date, then oldest created_at.
    """
    date_threshold = (
        datetime.now(timezone.utc) - timedelta(days=max(0, max_age_days))
    ).date().isoformat()
    return query_db(
        """
        SELECT
            c.cluster_id,
            c.description,
            c.category,
            c.place,
            c.created_at,
            c.processed,
            COUNT(a.id) AS article_count,
            COUNT(DISTINCT a.source) AS source_count,
            MAX(a.date) AS latest_date
        FROM clusters c
        JOIN topic_clusters tc ON tc.cluster_id = c.cluster_id
        JOIN raw_articles a ON a.id = tc.article_id
        WHERE c.processed = 0
          AND c.description IS NOT NULL
          AND TRIM(c.description) != ''
        GROUP BY
            c.cluster_id,
            c.description,
            c.category,
            c.place,
            c.created_at,
            c.processed
        HAVING MAX(a.date) >= ?
        ORDER BY
            article_count DESC,
            source_count DESC,
            latest_date DESC,
            c.created_at ASC
        LIMIT ?
        """,
        (date_threshold, limit),
    )


def mark_cluster_processed(cluster_id: str) -> None:
    with get_engine().begin() as conn:
        conn.execute(
            text(
                "UPDATE clusters SET processed = 1 WHERE cluster_id = :cluster_id"
            ),
            {"cluster_id": cluster_id},
        )


def _json_bind(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value)


def _json_sql(name: str) -> str:
    """Postgres needs an explicit jsonb cast; SQLite stores JSON as text."""
    if get_engine().dialect.name == "postgresql":
        return f"CAST(:{name} AS jsonb)"
    return f":{name}"


def insert_verified_article(
    *,
    cluster_id: str,
    title: str,
    content: str,
    image_url: str | None = None,
    date: str | None = None,
    sources: str | None = None,
    category: str | None = None,
    place: str | None = None,
    status: str = "published",
    confidence: str | None = None,
    confidence_score: float | None = None,
    source_scores: list[Any] | dict[str, Any] | None = None,
    audit_json: dict[str, Any] | list[Any] | None = None,
) -> str:
    """
    Upsert a verified article for cluster_id.
    Returns the article id. Does not overwrite created_at on conflict.
    """
    article_id = hashlib.sha256(f"verified:{cluster_id}".encode()).hexdigest()
    slug = article_slug(title, cluster_id)
    created_at = datetime.now().isoformat()
    source_scores_sql = _json_sql("source_scores")
    audit_json_sql = _json_sql("audit_json")
    with get_engine().begin() as conn:
        conn.execute(
            text(
                f"""
                INSERT INTO verified_articles (
                    id, cluster_id, slug, title, content, category, place,
                    image_url, date, sources, status, confidence,
                    confidence_score, source_scores, audit_json, created_at
                )
                VALUES (
                    :id, :cluster_id, :slug, :title, :content, :category,
                    :place, :image_url, :date, :sources, :status, :confidence,
                    :confidence_score, {source_scores_sql}, {audit_json_sql},
                    :created_at
                )
                ON CONFLICT (cluster_id) DO UPDATE SET
                    slug = EXCLUDED.slug,
                    title = EXCLUDED.title,
                    content = EXCLUDED.content,
                    category = EXCLUDED.category,
                    place = EXCLUDED.place,
                    image_url = EXCLUDED.image_url,
                    date = EXCLUDED.date,
                    sources = EXCLUDED.sources,
                    status = EXCLUDED.status,
                    confidence = EXCLUDED.confidence,
                    confidence_score = EXCLUDED.confidence_score,
                    source_scores = EXCLUDED.source_scores,
                    audit_json = EXCLUDED.audit_json
                """
            ),
            {
                "id": article_id,
                "cluster_id": cluster_id,
                "slug": slug,
                "title": title,
                "content": content,
                "category": normalize_category(category),
                "place": normalize_place(place),
                "image_url": image_url,
                "date": date,
                "sources": sources,
                "status": status,
                "confidence": confidence,
                "confidence_score": confidence_score,
                "source_scores": _json_bind(source_scores),
                "audit_json": _json_bind(audit_json),
                "created_at": created_at,
            },
        )
    from common.indexing import index_verified_article

    index_verified_article(
        cluster_id=cluster_id,
        title=title,
        content=content,
        date=date,
        status=status,
    )
    return article_id


def update_verified_article_image(article_id: str, image_url: str) -> None:
    """Set image_url for an existing verified article."""
    with get_engine().begin() as conn:
        conn.execute(
            text(
                """
                UPDATE verified_articles
                SET image_url = :image_url
                WHERE id = :id
                """
            ),
            {"id": article_id, "image_url": image_url},
        )


_VERIFIED_SELECT = """
    SELECT id, cluster_id, slug, title, content, category, place, image_url,
           date, sources, status, confidence, confidence_score, source_scores,
           audit_json, created_at
    FROM verified_articles
"""


def fetch_verified_article(cluster_id: str) -> dict | None:
    rows = query_db(
        _VERIFIED_SELECT + " WHERE cluster_id = ?",
        (cluster_id,),
    )
    return rows[0] if rows else None


_PUBLISHED_SELECT = """
    SELECT
        v.id, v.cluster_id, v.slug, v.title, v.content, v.category, v.place,
        v.image_url, v.date, v.sources, v.status, v.confidence,
        v.confidence_score, v.source_scores, v.audit_json, v.created_at,
        COALESCE(stats.cluster_size, 0) AS cluster_size,
        COALESCE(stats.source_count, 0) AS source_count
    FROM verified_articles v
    LEFT JOIN (
        SELECT
            tc.cluster_id,
            COUNT(a.id) AS cluster_size,
            COUNT(DISTINCT a.source) AS source_count
        FROM topic_clusters tc
        JOIN raw_articles a ON a.id = tc.article_id
        GROUP BY tc.cluster_id
    ) stats ON stats.cluster_id = v.cluster_id
"""


def fetch_published_articles(
    *, limit: int = 100, category: str | None = None
) -> list[dict]:
    """
    Published verified articles ranked by cluster importance.

    Order: cluster_size DESC, source_count DESC, then newest date/created_at.
    """
    if category:
        return query_db(
            _PUBLISHED_SELECT
            + """
            WHERE v.status = 'published' AND LOWER(v.category) = LOWER(?)
            ORDER BY
                cluster_size DESC,
                source_count DESC,
                COALESCE(v.date, v.created_at) DESC
            LIMIT ?
            """,
            (category, limit),
        )
    return query_db(
        _PUBLISHED_SELECT
        + """
        WHERE v.status = 'published'
        ORDER BY
            cluster_size DESC,
            source_count DESC,
            COALESCE(v.date, v.created_at) DESC
        LIMIT ?
        """,
        (limit,),
    )


def fetch_published_article_by_slug(slug: str) -> dict | None:
    rows = query_db(
        _VERIFIED_SELECT + " WHERE slug = ? AND status = 'published'",
        (slug,),
    )
    return rows[0] if rows else None


def fetch_verified_articles(
    date_threshold: str,
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """
    Recent verified articles on/after date_threshold (by article date, else created_at).

    Optional status filter. Ordered by newest date first.
    """
    if status:
        return query_db(
            _VERIFIED_SELECT
            + """
            WHERE COALESCE(date, created_at) >= ?
              AND status = ?
            ORDER BY COALESCE(date, created_at) DESC
            LIMIT ?
            """,
            (date_threshold, status, limit),
        )
    return query_db(
        _VERIFIED_SELECT
        + """
        WHERE COALESCE(date, created_at) >= ?
        ORDER BY COALESCE(date, created_at) DESC
        LIMIT ?
        """,
        (date_threshold, limit),
    )


def fetch_all_verified_articles() -> list[dict]:
    return query_db(
        """
        SELECT cluster_id, title, content, date, status
        FROM verified_articles
        ORDER BY created_at ASC
        """
    )


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
    if source:
        return query_db(
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
        )
    return query_db(
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
    )


def fetch_clusters_with_descriptions() -> list[dict]:
    """Return clusters that have a non-null description."""
    return query_db(
        """
        SELECT cluster_id, description, created_at
        FROM clusters
        WHERE description IS NOT NULL AND TRIM(description) != ''
        ORDER BY created_at ASC
        """
    )


def fetch_clusters_without_descriptions() -> list[str]:
    """Return cluster_ids missing a description."""
    rows = query_db(
        """
        SELECT cluster_id
        FROM clusters
        WHERE description IS NULL OR TRIM(description) = ''
        ORDER BY created_at ASC
        """
    )
    return [row["cluster_id"] for row in rows]
