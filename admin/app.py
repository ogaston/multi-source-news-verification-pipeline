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

DB_NAME = os.environ.get("DB_NAME", "dominican_news_repository.db")
ADMIN_SECRET_KEY = os.environ.get("ADMIN_SECRET_KEY", "dev-insecure-secret-change-me")

engine = create_engine(
    f"sqlite:///{DB_NAME}",
    connect_args={"check_same_thread": False},
)

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
