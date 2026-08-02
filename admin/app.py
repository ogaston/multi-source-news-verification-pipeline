"""FastAPI + SQLAdmin entrypoint."""

import os

from fastapi import FastAPI
from sqladmin import Admin
from starlette.middleware.sessions import SessionMiddleware

from admin.auth import AdminAuth
from admin.views import (
    ClusterAdmin,
    RawArticleAdmin,
    TopicClusterAdmin,
    VerifiedArticleAdmin,
)
from common.db import get_engine

ADMIN_SECRET_KEY = os.environ.get("ADMIN_SECRET_KEY", "dev-insecure-secret-change-me")

engine = get_engine()

app = FastAPI(title="Ojo Crítico admin")
app.add_middleware(SessionMiddleware, secret_key=ADMIN_SECRET_KEY)

authentication_backend = AdminAuth(secret_key=ADMIN_SECRET_KEY)
admin = Admin(
    app,
    engine,
    title="Ojo Crítico — Multi-Source News Verification Pipeline",
    authentication_backend=authentication_backend,
)
admin.add_view(RawArticleAdmin)
admin.add_view(TopicClusterAdmin)
admin.add_view(ClusterAdmin)
admin.add_view(VerifiedArticleAdmin)
