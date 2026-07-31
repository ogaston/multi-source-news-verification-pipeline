"""Add nullable confidence fields to verified_articles.

Revision ID: 002_verified_confidence
Revises: 001_initial
Create Date: 2026-07-30

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_verified_confidence"
down_revision: Union[str, Sequence[str], None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "verified_articles",
        sa.Column("confidence", sa.String(), nullable=True),
    )
    op.add_column(
        "verified_articles",
        sa.Column("confidence_score", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("verified_articles", "confidence_score")
    op.drop_column("verified_articles", "confidence")
