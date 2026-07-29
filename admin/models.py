"""SQLAlchemy models mirroring the pipeline SQLite schema."""

from sqlalchemy import Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class RawArticle(Base):
    __tablename__ = "raw_articles"

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
    created_at: Mapped[str] = mapped_column(String, nullable=False)
