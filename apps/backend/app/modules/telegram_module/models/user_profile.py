from typing import TYPE_CHECKING

from app.modules import Base, TimestampMixin
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from .telegram_user import TelegramUser


class UserProfile(Base, TimestampMixin):
    telegram_user_id: Mapped[int] = mapped_column(
        ForeignKey("telegramuser.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    note: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    telegram_user: Mapped["TelegramUser"] = relationship(
        back_populates="user_profile",
    )
