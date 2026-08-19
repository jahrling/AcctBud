"""check_in and check_in_item tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-19
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "check_in",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("for_date", sa.String, nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("followup_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.String,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column(
            "journal_written",
            sa.Boolean,
            nullable=False,
            server_default="0",
        ),
    )
    op.create_table(
        "check_in_item",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("check_in_id", sa.Integer, sa.ForeignKey("check_in.id"), nullable=False),
        sa.Column("task_id", sa.Integer, nullable=False),
        sa.Column("task_title", sa.String, nullable=False),
        sa.Column("task_category", sa.String, nullable=False),
        sa.Column("done", sa.Boolean, nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("check_in_item")
    op.drop_table("check_in")
