"""Shared pytest fixtures for DB-backed tests (SQLAlchemy + temp SQLite)."""

from __future__ import annotations

import pytest
from sqlalchemy import text

import common.config as config
import common.db as db
from common.models import Base


@pytest.fixture
def sqlalchemy_db(tmp_path, monkeypatch):
    """
    Point the app engine at a temp SQLite file and create the schema.

    Production uses PostgreSQL; unit tests use SQLite via the same SQLAlchemy
    models/API so no live Postgres is required.
    """
    db_path = tmp_path / "test_news.db"
    url = f"sqlite+pysqlite:///{db_path}"
    monkeypatch.setattr(config, "DATABASE_URL", url)
    monkeypatch.setattr(db, "DATABASE_URL", url)
    db.reset_engine()
    Base.metadata.create_all(db.get_engine())
    yield db_path
    db.reset_engine()


def insert_raw_articles(rows: list[dict]) -> None:
    """Insert raw_articles rows (dict keys = column names)."""
    if not rows:
        return
    cols = list(rows[0].keys())
    col_list = ", ".join(cols)
    placeholders = ", ".join(f":{c}" for c in cols)
    with db.get_engine().begin() as conn:
        conn.execute(
            text(f"INSERT INTO raw_articles ({col_list}) VALUES ({placeholders})"),
            rows,
        )
