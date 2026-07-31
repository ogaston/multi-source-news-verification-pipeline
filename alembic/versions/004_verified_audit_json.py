"""Add source_scores and audit_json JSONB to verified_articles.

Revision ID: 004_verified_audit_json
Revises: 003_verified_category
Create Date: 2026-07-30

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "004_verified_audit_json"
down_revision: Union[str, Sequence[str], None] = "003_verified_category"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "verified_articles",
        sa.Column("source_scores", JSONB(), nullable=True),
    )
    op.add_column(
        "verified_articles",
        sa.Column("audit_json", JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("verified_articles", "audit_json")
    op.drop_column("verified_articles", "source_scores")
