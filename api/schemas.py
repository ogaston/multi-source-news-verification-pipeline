"""Pydantic response models matching website Article types."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ConfidenceLevel = Literal["alta", "media", "baja", "en_revision"]


class ArticleSource(BaseModel):
    name: str
    url: str


class Article(BaseModel):
    slug: str
    category: str
    title: str
    summary: str
    body: list[str]
    image: str | None = None
    imageAlt: str | None = None
    imageCaption: str | None = None
    readTime: str
    confidence: ConfidenceLevel
    sources: list[ArticleSource] = Field(default_factory=list)
    date: str
    perspectives: list[str] | None = None
