"""Initial schema matching former SQLite tables.

Revision ID: 001_initial
Revises:
Create Date: 2026-07-30

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "raw_articles",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("url", sa.String(), unique=True),
        sa.Column("source", sa.String()),
        sa.Column("title", sa.String()),
        sa.Column("content", sa.Text()),
        sa.Column("date", sa.String()),
        sa.Column("author", sa.String()),
        sa.Column("category", sa.String()),
        sa.Column("scraped_at", sa.String()),
        sa.Column("processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("article_key", sa.String()),
    )
    op.create_index(
        "idx_raw_articles_article_key",
        "raw_articles",
        ["article_key"],
        unique=True,
        postgresql_where=sa.text("article_key IS NOT NULL"),
    )

    op.create_table(
        "clusters",
        sa.Column("cluster_id", sa.String(), primary_key=True),
        sa.Column("description", sa.Text()),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("processed", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "topic_clusters",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("cluster_id", sa.String(), nullable=False),
        sa.Column("article_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.UniqueConstraint("cluster_id", "article_id"),
    )

    op.create_table(
        "verified_articles",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("cluster_id", sa.String(), nullable=False, unique=True),
        sa.Column("slug", sa.String(), nullable=False, unique=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("image_url", sa.String()),
        sa.Column("date", sa.String()),
        sa.Column("sources", sa.String()),
        sa.Column("status", sa.String(), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.String(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("verified_articles")
    op.drop_table("topic_clusters")
    op.drop_table("clusters")
    op.drop_index("idx_raw_articles_article_key", table_name="raw_articles")
    op.drop_table("raw_articles")
