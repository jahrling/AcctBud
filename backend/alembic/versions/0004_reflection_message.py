"""reflection_message table and check_in reflection columns

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-19
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reflection_message",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "check_in_id", sa.Integer, sa.ForeignKey("check_in.id"), nullable=False
        ),
        sa.Column("role", sa.String, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.add_column(
        "check_in",
        sa.Column(
            "reflection_finished",
            sa.Boolean,
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "check_in",
        sa.Column(
            "reflection_journal_written",
            sa.Boolean,
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("check_in", "reflection_journal_written")
    op.drop_column("check_in", "reflection_finished")
    op.drop_table("reflection_message")
