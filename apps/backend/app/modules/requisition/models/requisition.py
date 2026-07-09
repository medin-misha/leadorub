from typing import Any, TYPE_CHECKING

from sqlalchemy import ForeignKey, String, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.modules import Base, TimestampMixin

if TYPE_CHECKING:
    from app.modules.telegram_module.models.telegram_user import TelegramUser


class Requisition(Base, TimestampMixin):
    """Универсальная модель заявки.

    Хранит информацию о пользователе, типе продукта (консультация, сообщество и др.),
    текущем статусе и произвольном payload в формате JSON, что позволяет поддерживать
    любые типы опросников без изменения схемы БД.
    """

    __tablename__ = "requisitions"

    # Ссылка на пользователя, подавшего заявку
    telegram_user_id: Mapped[int] = mapped_column(
        ForeignKey("telegramuser.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Тип продукта (например, 'consultation', 'community')
    type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Статус заявки: 'pending', 'in_progress', 'approved', 'rejected'
    status: Mapped[str] = mapped_column(
        String(30), default="pending", nullable=False, index=True
    )

    # Произвольный payload с ответами на вопросы
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Комментарий администратора при обработке
    admin_comment: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # Отношение к TelegramUser (автоматически подгружается через selectin)
    telegram_user: Mapped["TelegramUser"] = relationship(
        "TelegramUser",
        lazy="selectin",
    )
