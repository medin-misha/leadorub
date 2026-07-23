from typing import TYPE_CHECKING
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, String, event, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.orm.attributes import NO_VALUE

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
    # Момент последней ФАКТИЧЕСКОЙ смены state (UTC). Поддерживается listener'ом
    # ниже, а не onupdate: updated_at бампается любым апдейтом строки, а нам
    # нужен именно вход в состояние — от него капельные рассылки считают дни.
    state_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    telegram_user: Mapped["TelegramUser"] = relationship(
        back_populates="user_stats",
    )

    # Композитный индекс под выборку капельных рассылок:
    # WHERE state = :s AND state_changed_at BETWEEN :a AND :b
    __table_args__ = (
        Index("ix_userstats_state_changed", "state", "state_changed_at"),
    )


# active_history=True заставляет SQLAlchemy подгрузить старое значение перед
# записью нового — иначе для persistent-объектов oldvalue был бы NO_VALUE и
# отличить реальную смену состояния от записи того же значения нельзя.
@event.listens_for(UserStats.state, "set", active_history=True)
def _touch_state_changed_at(
    target: UserStats, value: str | None, oldvalue: object, initiator: object
) -> None:
    if oldvalue is NO_VALUE:
        # Новый объект: считаем сменой только установку непустого состояния.
        changed = value is not None
    else:
        changed = value != oldvalue
    if changed:
        target.state_changed_at = datetime.now(timezone.utc)
