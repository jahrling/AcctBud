"""daily_summary table

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-21
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "daily_summary",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("for_date", sa.String, unique=True, nullable=False),
        sa.Column("summary_text", sa.Text, nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("model_used", sa.String, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("daily_summary")
