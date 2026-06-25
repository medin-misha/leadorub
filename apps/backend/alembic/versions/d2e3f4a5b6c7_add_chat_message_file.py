"""add chat_message.file_id, make text nullable

Revision ID: d2e3f4a5b6c7
Revises: c1a2b3d4e5f6
Create Date: 2026-06-25 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d2e3f4a5b6c7"
down_revision: Union[str, Sequence[str], None] = "c1a2b3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("chat_message", sa.Column("file_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_chat_message_file_id",
        "chat_message",
        "file",
        ["file_id"],
        ["id"],
        ondelete="SET NULL",
    )
    # Подпись к вложению опциональна → текст становится nullable.
    op.alter_column("chat_message", "text", existing_type=sa.Text(), nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column("chat_message", "text", existing_type=sa.Text(), nullable=False)
    op.drop_constraint("fk_chat_message_file_id", "chat_message", type_="foreignkey")
    op.drop_column("chat_message", "file_id")
