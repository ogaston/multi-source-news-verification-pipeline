"""FastAPI + SQLAdmin entrypoint."""

import os

from fastapi import FastAPI
from sqladmin import Admin
from sqlalchemy import create_engine
from starlette.middleware.sessions import SessionMiddleware

from admin.auth import AdminAuth
from admin.views import (
    ClusterAdmin,
    RawArticleAdmin,
    TopicClusterAdmin,
    VerifiedArticleAdmin,
)

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg://news:news@localhost:5432/news",
)
ADMIN_SECRET_KEY = os.environ.get("ADMIN_SECRET_KEY", "dev-insecure-secret-change-me")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

app = FastAPI(title="News pipeline admin")
app.add_middleware(SessionMiddleware, secret_key=ADMIN_SECRET_KEY)

authentication_backend = AdminAuth(secret_key=ADMIN_SECRET_KEY)
admin = Admin(
    app,
    engine,
    title="News Pipeline Admin",
    authentication_backend=authentication_backend,
)
admin.add_view(RawArticleAdmin)
admin.add_view(TopicClusterAdmin)
admin.add_view(ClusterAdmin)
admin.add_view(VerifiedArticleAdmin)
