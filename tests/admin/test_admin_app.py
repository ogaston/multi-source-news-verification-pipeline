"""Admin application wiring tests that do not connect to PostgreSQL."""

from admin.app import app, engine
from common.db import get_engine


def test_admin_uses_shared_database_engine():
    assert app.title == "Ojo Crítico admin"
    assert engine is get_engine()
