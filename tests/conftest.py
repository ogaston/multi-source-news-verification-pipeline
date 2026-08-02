"""Shared pytest fixtures for DB-backed tests (SQLAlchemy + PostgreSQL)."""

from __future__ import annotations

import os

import pytest
from sqlalchemy import text

import common.config as config
import common.db as db
from common.models import Base

# API modules read API_KEY at import time. Force a stable value so CI env
# (e.g. API_KEY=ci-test-api-key) cannot diverge from Bearer tokens in tests.
os.environ["API_KEY"] = "test-api-key"


@pytest.fixture
def sqlalchemy_db(monkeypatch):
    """
    Recreate the schema in a dedicated PostgreSQL test database.

    TEST_DATABASE_URL is intentionally required: this fixture drops every table
    in that database and must never fall back to a development/production URL.
    """
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.fail(
            "TEST_DATABASE_URL is required for DB-backed tests "
            "(for example postgresql+psycopg://news:news@localhost:5432/news_test)"
        )
    if not url.startswith(("postgresql://", "postgresql+psycopg://")):
        pytest.fail("TEST_DATABASE_URL must point to PostgreSQL")

    monkeypatch.setattr(config, "DATABASE_URL", url)
    monkeypatch.setattr(db, "DATABASE_URL", url)
    db.reset_engine()
    Base.metadata.drop_all(db.get_engine())
    Base.metadata.create_all(db.get_engine())
    yield db.get_engine()
    Base.metadata.drop_all(db.get_engine())
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
