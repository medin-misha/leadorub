from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.modules import Base, TimestampMixin

if TYPE_CHECKING:
    from .user_profile import UserProfile
    from .user_stats import UserStats


class TelegramUser(Base, TimestampMixin):
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_blocket_bot: Mapped[bool] = mapped_column(default=False)
    language_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    user_profile: Mapped["UserProfile | None"] = relationship(
        back_populates="telegram_user",
        uselist=False,
        lazy="selectin",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    user_stats: Mapped["UserStats | None"] = relationship(
        back_populates="telegram_user",
        uselist=False,
        lazy="selectin",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
