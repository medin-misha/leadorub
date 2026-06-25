from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, String, Text, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.modules import Base, TimestampMixin

if TYPE_CHECKING:
    from app.modules.file_module.models import File


class ChatMessage(Base, TimestampMixin):
    """Одно сообщение чата поддержки между пользователем и администратором.

    Лог сообщений плоский: одна строка = одно сообщение. `direction` различает,
    кто автор. История диалога с пользователем — это все строки с одним
    `telegram_user_id`, отсортированные по `created_at`/`id`.

    Сообщение содержит текст и/или вложение (`file_id` → модель File бэкенда).
    """

    # Конвенция Base дала бы имя "chatmessage"; задаём читаемое имя явно.
    __tablename__ = "chat_message"
    __table_args__ = (
        # Композитный индекс под выборку треда и агрегата списка диалогов:
        # фильтр по пользователю + сортировка по времени.
        Index("ix_chat_message_user_created", "telegram_user_id", "created_at"),
    )

    telegram_user_id: Mapped[int] = mapped_column(
        ForeignKey("telegramuser.id", ondelete="CASCADE"),
        nullable=False,
    )
    # 'user' — сообщение пользователя, 'admin' — ответ администратора.
    direction: Mapped[str] = mapped_column(String(8), nullable=False)
    # Текст или подпись к вложению. Может быть NULL, если сообщение — только файл.
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    # message_id сообщения пользователя в Telegram (для реакций/референса). У
    # ответов администратора отсутствует.
    tg_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    # Опциональное вложение: id модели File бэкенда. SET NULL — удаление файла
    # не удаляет сообщение.
    file_id: Mapped[int | None] = mapped_column(
        ForeignKey("file.id", ondelete="SET NULL"), nullable=True
    )
    # Прочитано ли админом. Осмысленно только для direction='user'.
    is_read: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), nullable=False
    )

    # selectin — грузим вложение вместе с сообщением, без ленивой подгрузки
    # (ленивый доступ в async упал бы с MissingGreenlet).
    file: Mapped["File | None"] = relationship(lazy="selectin")

    @property
    def file_name(self) -> str | None:
        """Имя файла вложения для сериализации (ChatMessageRead.file_name)."""
        return self.file.name if self.file else None
