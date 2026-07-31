"""Add nullable category to verified_articles; default status published.

Revision ID: 003_verified_category
Revises: 002_verified_confidence
Create Date: 2026-07-30

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_verified_category"
down_revision: Union[str, Sequence[str], None] = "002_verified_confidence"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "verified_articles",
        sa.Column("category", sa.String(), nullable=True),
    )
    op.alter_column(
        "verified_articles",
        "status",
        server_default="published",
        existing_type=sa.String(),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "verified_articles",
        "status",
        server_default="draft",
        existing_type=sa.String(),
        existing_nullable=False,
    )
    op.drop_column("verified_articles", "category")
