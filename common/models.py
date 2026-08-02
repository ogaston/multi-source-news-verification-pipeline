"""SQLAlchemy models — single source of truth for the pipeline schema."""

from typing import Any

from sqlalchemy import Float, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import JSON


class Base(DeclarativeBase):
    pass


class RawArticle(Base):
    __tablename__ = "raw_articles"
    __table_args__ = (
        Index(
            "idx_raw_articles_article_key",
            "article_key",
            unique=True,
            postgresql_where=text("article_key IS NOT NULL"),
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    url: Mapped[str | None] = mapped_column(String, unique=True)
    source: Mapped[str | None] = mapped_column(String)
    title: Mapped[str | None] = mapped_column(String)
    content: Mapped[str | None] = mapped_column(Text)
    date: Mapped[str | None] = mapped_column(String)
    author: Mapped[str | None] = mapped_column(String)
    category: Mapped[str | None] = mapped_column(String)
    scraped_at: Mapped[str | None] = mapped_column(String)
    processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    article_key: Mapped[str | None] = mapped_column(String)


class TopicCluster(Base):
    __tablename__ = "topic_clusters"
    __table_args__ = (UniqueConstraint("cluster_id", "article_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cluster_id: Mapped[str] = mapped_column(String, nullable=False)
    article_id: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False)


class Cluster(Base):
    __tablename__ = "clusters"

    cluster_id: Mapped[str] = mapped_column(String, primary_key=True)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String)
    place: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class VerifiedArticle(Base):
    __tablename__ = "verified_articles"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    cluster_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String)
    place: Mapped[str | None] = mapped_column(String)
    image_url: Mapped[str | None] = mapped_column(String)
    date: Mapped[str | None] = mapped_column(String)
    sources: Mapped[str | None] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="published", nullable=False)
    # Populated by Analyzer (REQ-AGENT-001); nullable until then.
    confidence: Mapped[str | None] = mapped_column(String)
    confidence_score: Mapped[float | None] = mapped_column(Float)
    source_scores: Mapped[list[Any] | None] = mapped_column(JSON)
    audit_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
