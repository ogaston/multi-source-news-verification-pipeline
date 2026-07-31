"""
One-shot SQLite → PostgreSQL data copy (ops only).

Do NOT call from application startup. Run explicitly after Alembic schema migrate:

  docker compose run --rm scheduler alembic upgrade head
  docker compose run --rm scheduler python -m scripts.migrate_sqlite_to_postgres
  docker compose run --rm scheduler python -m scripts.migrate_sqlite_to_postgres --dry-run

Chroma: article/cluster vector IDs must stay stable. This script copies primary
keys verbatim (`id`, `cluster_id`, membership `id`) so existing Chroma indexes
remain valid.

Rollback: keep the SQLite file as a backup until PostgreSQL is validated in
production (MCP search + admin UI show matching data and row counts).
"""

from __future__ import annotations

import argparse
import logging
import os
import sqlite3
import sys
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from common.config import DATABASE_URL, DB_NAME
from common.db import article_slug

logger = logging.getLogger("migrate_sqlite_to_postgres")

TABLE_ORDER = (
    "raw_articles",
    "clusters",
    "topic_clusters",
    "verified_articles",
)

TABLE_COLUMNS: dict[str, tuple[str, ...]] = {
    "raw_articles": (
        "id",
        "url",
        "source",
        "title",
        "content",
        "date",
        "author",
        "category",
        "scraped_at",
        "processed",
        "article_key",
    ),
    "clusters": ("cluster_id", "description", "created_at", "processed"),
    "topic_clusters": ("id", "cluster_id", "article_id", "created_at"),
    "verified_articles": (
        "id",
        "cluster_id",
        "slug",
        "title",
        "content",
        "category",
        "image_url",
        "date",
        "sources",
        "status",
        "created_at",
    ),
}

# Conflict target for ON CONFLICT DO NOTHING (PK or unique key).
CONFLICT_TARGETS: dict[str, str] = {
    "raw_articles": "id",
    "clusters": "cluster_id",
    "topic_clusters": "id",
    "verified_articles": "id",
}


def _sqlite_table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {row[1] for row in rows}


def _fetch_sqlite_rows(
    conn: sqlite3.Connection, table: str
) -> tuple[list[str], list[tuple[Any, ...]]]:
    available = _sqlite_table_columns(conn, table)
    if not available:
        logger.warning("SQLite table missing: %s", table)
        return [], []

    columns = [c for c in TABLE_COLUMNS[table] if c in available]
    missing = [c for c in TABLE_COLUMNS[table] if c not in available]
    if missing:
        logger.warning(
            "SQLite %s missing columns (filled with defaults/NULL): %s",
            table,
            ", ".join(missing),
        )

    select_cols = ", ".join(columns)
    rows = conn.execute(f"SELECT {select_cols} FROM {table}").fetchall()

    # Pad missing columns for insert shape.
    full_cols = list(TABLE_COLUMNS[table])
    out: list[tuple[Any, ...]] = []
    for row in rows:
        by_name = dict(zip(columns, row, strict=True))
        values = []
        for col in full_cols:
            if col in by_name and by_name[col] is not None:
                values.append(by_name[col])
            elif col == "processed":
                values.append(0)
            elif col == "status":
                values.append("draft")
            elif col == "slug":
                values.append(
                    article_slug(
                        str(by_name.get("title") or ""),
                        str(by_name.get("cluster_id") or ""),
                    )
                )
            else:
                values.append(None)
        out.append(tuple(values))
    return full_cols, out


def _count_postgres(engine: Engine, table: str) -> int:
    with engine.connect() as conn:
        return int(conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one())


def _insert_rows(
    engine: Engine,
    table: str,
    columns: list[str],
    rows: list[tuple[Any, ...]],
    *,
    dry_run: bool,
) -> tuple[int, int]:
    """Returns (inserted_or_would_insert, skipped_conflicts_estimate)."""
    if not rows:
        return 0, 0

    before = _count_postgres(engine, table) if not dry_run else 0
    if dry_run:
        logger.info(
            "[dry-run] would insert up to %d rows into %s (ON CONFLICT DO NOTHING)",
            len(rows),
            table,
        )
        return len(rows), 0

    col_list = ", ".join(columns)
    placeholders = ", ".join(f":{c}" for c in columns)
    conflict = CONFLICT_TARGETS[table]
    sql = text(
        f"""
        INSERT INTO {table} ({col_list})
        VALUES ({placeholders})
        ON CONFLICT ({conflict}) DO NOTHING
        """
    )
    payload = [dict(zip(columns, row, strict=True)) for row in rows]
    with engine.begin() as conn:
        conn.execute(sql, payload)
        # Reset identity sequence for topic_clusters so future inserts don't collide.
        if table == "topic_clusters":
            conn.execute(
                text(
                    """
                    SELECT setval(
                        pg_get_serial_sequence('topic_clusters', 'id'),
                        COALESCE((SELECT MAX(id) FROM topic_clusters), 1),
                        true
                    )
                    """
                )
            )

    after = _count_postgres(engine, table)
    inserted = after - before
    skipped = len(rows) - inserted
    return inserted, max(skipped, 0)


def migrate(
    *,
    sqlite_path: str,
    database_url: str,
    dry_run: bool = False,
) -> int:
    logger.info("Source SQLite: %s", sqlite_path)
    logger.info("Target Postgres: %s", database_url)
    logger.info("Dry run: %s", dry_run)

    if not os.path.isfile(sqlite_path):
        raise FileNotFoundError(sqlite_path)

    sqlite_conn = sqlite3.connect(sqlite_path)
    engine = create_engine(database_url, pool_pre_ping=True)

    try:
        # Connectivity / schema presence check.
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            for table in TABLE_ORDER:
                conn.execute(text(f"SELECT 1 FROM {table} LIMIT 0"))

        totals: dict[str, dict[str, int]] = {}
        for table in TABLE_ORDER:
            columns, rows = _fetch_sqlite_rows(sqlite_conn, table)
            source_count = len(rows)
            inserted, skipped = _insert_rows(
                engine, table, columns, rows, dry_run=dry_run
            )
            target_count = (
                source_count if dry_run else _count_postgres(engine, table)
            )
            totals[table] = {
                "source": source_count,
                "inserted": inserted,
                "skipped": skipped,
                "target": target_count,
            }
            logger.info(
                "%s: source=%d inserted=%d skipped=%d target_total=%d",
                table,
                source_count,
                inserted,
                skipped,
                target_count,
            )

        logger.info("Migration summary: %s", totals)
        if dry_run:
            logger.info("Dry-run complete; no rows written.")
        else:
            mismatches = [
                t
                for t, c in totals.items()
                if c["source"] > 0 and c["target"] < c["source"]
            ]
            if mismatches:
                logger.warning(
                    "Target has fewer rows than source for: %s "
                    "(re-run is safe; conflicts are skipped)",
                    ", ".join(mismatches),
                )
        return 0
    finally:
        sqlite_conn.close()
        engine.dispose()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Copy SQLite news DB into PostgreSQL (one-shot ops script)."
    )
    parser.add_argument(
        "--sqlite-path",
        default=DB_NAME,
        help=f"Path to source SQLite file (default: {DB_NAME})",
    )
    parser.add_argument(
        "--database-url",
        default=DATABASE_URL,
        help="Target SQLAlchemy DATABASE_URL",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Count/validate only; do not write to Postgres",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    try:
        return migrate(
            sqlite_path=args.sqlite_path,
            database_url=args.database_url,
            dry_run=args.dry_run,
        )
    except FileNotFoundError:
        logger.error("SQLite file not found: %s", args.sqlite_path)
        return 1
    except Exception:
        logger.exception("Migration failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
