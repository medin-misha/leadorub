"""add RMQ transactional outbox

Revision ID: e3f4a5b6c7d8
Revises: 9e5d02a48c13
Create Date: 2026-07-12 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e3f4a5b6c7d8"
down_revision: Union[str, Sequence[str], None] = "9e5d02a48c13"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rmq_outbox_message",
        sa.Column("message_id", sa.String(length=36), nullable=False),
        sa.Column("event", sa.String(length=255), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("exchange_name", sa.String(length=255), nullable=False),
        sa.Column("exchange_type", sa.String(length=32), nullable=False),
        sa.Column("routing_key", sa.String(length=255), nullable=False),
        sa.Column("queue_name", sa.String(length=255), nullable=True),
        sa.Column("source", sa.String(length=255), nullable=False),
        sa.Column("correlation_id", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("message_id"),
    )
    op.create_index(
        "ix_rmq_outbox_dispatch",
        "rmq_outbox_message",
        ["status", "available_at", "id"],
    )
    op.create_index(
        "ix_rmq_outbox_locked_until", "rmq_outbox_message", ["locked_until"]
    )


def downgrade() -> None:
    op.drop_index("ix_rmq_outbox_locked_until", table_name="rmq_outbox_message")
    op.drop_index("ix_rmq_outbox_dispatch", table_name="rmq_outbox_message")
    op.drop_table("rmq_outbox_message")
