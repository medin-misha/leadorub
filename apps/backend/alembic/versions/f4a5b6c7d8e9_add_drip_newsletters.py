"""add drip newsletters and user state change tracking

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-07-20 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f4a5b6c7d8e9"
down_revision: Union[str, Sequence[str], None] = "e3f4a5b6c7d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Момент последней фактической смены user_stats.state — точка отсчёта
    # для капельных рассылок.
    op.add_column(
        "userstats",
        sa.Column("state_changed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_userstats_state_changed",
        "userstats",
        ["state", "state_changed_at"],
    )
    # Бэкфилл: для уже существующих состояний берём updated_at как приближение,
    # иначе пользователи, вошедшие в состояние до деплоя, никогда не попадут
    # в выборку sweep'а.
    op.execute(
        "UPDATE userstats SET state_changed_at = updated_at WHERE state IS NOT NULL"
    )

    op.create_table(
        "dripnewsletter",
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("trigger_state", sa.String(length=255), nullable=False),
        sa.Column("days_offset", sa.Integer(), nullable=False),
        sa.Column("send_time", sa.Time(), nullable=False),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("use_buttons", sa.String(length=16), nullable=True),
        sa.Column("buttons", sa.JSON(), nullable=True),
        sa.Column("file_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
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
        sa.CheckConstraint("days_offset >= 0", name="ck_dripnewsletter_days_offset"),
        sa.ForeignKeyConstraint(["file_id"], ["file.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_dripnewsletter_active_state",
        "dripnewsletter",
        ["is_active", "trigger_state"],
    )

    op.create_table(
        "dripnewslettersend",
        sa.Column("drip_newsletter_id", sa.Integer(), nullable=False),
        sa.Column("telegram_user_id", sa.Integer(), nullable=False),
        sa.Column("broadcast_id", sa.String(length=64), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["drip_newsletter_id"], ["dripnewsletter.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["telegram_user_id"], ["telegramuser.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "drip_newsletter_id", "telegram_user_id", name="uq_dripsend_rule_user"
        ),
    )


def downgrade() -> None:
    op.drop_table("dripnewslettersend")
    op.drop_index("ix_dripnewsletter_active_state", table_name="dripnewsletter")
    op.drop_table("dripnewsletter")
    op.drop_index("ix_userstats_state_changed", table_name="userstats")
    op.drop_column("userstats", "state_changed_at")
