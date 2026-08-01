"""Add category/place to clusters and place to verified_articles.

Revision ID: 005_cluster_category_place
Revises: 004_verified_audit_json
Create Date: 2026-07-31

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_cluster_category_place"
down_revision: Union[str, Sequence[str], None] = "004_verified_audit_json"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("clusters", sa.Column("category", sa.String(), nullable=True))
    op.add_column("clusters", sa.Column("place", sa.String(), nullable=True))
    op.add_column(
        "verified_articles", sa.Column("place", sa.String(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("verified_articles", "place")
    op.drop_column("clusters", "place")
    op.drop_column("clusters", "category")
