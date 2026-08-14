"""push_subscription and notification_log tables

Revision ID: 0001
Revises:
Create Date: 2026-08-13
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "push_subscription",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("endpoint", sa.String, unique=True, nullable=False),
        sa.Column("subscription_json", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String, nullable=False, server_default="active"),
    )
    op.create_table(
        "notification_log",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("kind", sa.String, nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title", sa.String, nullable=False),
        sa.Column("body", sa.String, nullable=False),
        sa.Column("subscription_id", sa.Integer, nullable=False),
        sa.Column("result", sa.String, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("notification_log")
    op.drop_table("push_subscription")
