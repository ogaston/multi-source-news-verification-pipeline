"""Public FastAPI service for the Ojo Crítico website."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.routes.articles import router as articles_router
from common.config import ARTICLE_IMAGES_DIR

API_PORT = int(os.environ.get("API_PORT", "7002"))


def _cors_origins() -> list[str]:
    raw = os.environ.get(
        "WEBSITE_CORS_ORIGINS",
        "http://localhost:7003",
    )
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


app = FastAPI(title="Ojo Crítico public API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)
app.include_router(articles_router)

_article_images = Path(ARTICLE_IMAGES_DIR)
_article_images.mkdir(parents=True, exist_ok=True)
app.mount(
    "/media/articles",
    StaticFiles(directory=str(_article_images)),
    name="article-images",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
