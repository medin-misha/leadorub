from typing import TYPE_CHECKING
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.modules import Base, TimestampMixin

if TYPE_CHECKING:
    from .telegram_user import TelegramUser


class UserStats(Base, TimestampMixin):
    """
    Поведенческая статистика одного Telegram-пользователя.

    Хранит данные, которые меняются по ходу жизни пользователя в боте
    (последний заход, источник привлечения, текущее состояние диалога),
    в отличие от неизменной идентичности в `TelegramUser` и собираемого
    профиля в `UserProfile`. Связь один-к-одному с `TelegramUser`.
    """

    telegram_user_id: Mapped[int] = mapped_column(
        ForeignKey("telegramuser.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    # Последний заход пользователя. Обновляется при логине.
    # server_default гарантирует now() даже при прямой вставке без явного значения.
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=True
    )
    # Источник, из которого пришёл пользователь (deep-link payload, UTM и т.п.).
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Текущее состояние пользователя в диалоге бота (FSM-state).
    state: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telegram_user: Mapped["TelegramUser"] = relationship(
        back_populates="user_stats",
    )
