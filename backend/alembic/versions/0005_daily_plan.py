"""daily_plan and daily_plan_item tables

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "daily_plan",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("for_date", sa.String, unique=True, nullable=False),
        sa.Column("status", sa.String, nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("journal_written", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("llm_suggestion", sa.Text, nullable=True),
    )
    op.create_table(
        "daily_plan_item",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "plan_id",
            sa.Integer,
            sa.ForeignKey("daily_plan.id"),
            nullable=False,
        ),
        sa.Column("task_id", sa.Integer, nullable=False),
        sa.Column("task_title", sa.String, nullable=False),
        sa.Column("task_category", sa.String, nullable=False),
        sa.Column("is_key", sa.Boolean, nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("daily_plan_item")
    op.drop_table("daily_plan")
