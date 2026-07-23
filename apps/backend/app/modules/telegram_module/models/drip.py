from datetime import time

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.modules import Base, TimestampMixin


class DripNewsletter(Base, TimestampMixin):
    """
    Правило капельной рассылки: «пользователь вошёл в состояние trigger_state →
    через days_offset дней в send_time отправить сообщение».

    Контент (text/use_buttons/buttons/file_id) повторяет обычную рассылку и
    доставляется через тот же RMQ-контракт `telegram.newsletter` — бот не
    отличает капельную рассылку от обычной.
    """

    # Название для админки; на доставку не влияет.
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Состояние-триггер (значение user_stats.state, напр. "persona_start").
    trigger_state: Mapped[str] = mapped_column(String(255), nullable=False)
    # Через сколько дней после входа в состояние отправлять (0 = в тот же день).
    days_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    # Время отправки — «настенное» время в settings.drip_timezone, без tz.
    send_time: Mapped[time] = mapped_column(Time, nullable=False)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    # "INLINE" | "REPLY" — как в NewsletterRequest.
    use_buttons: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # Список кнопок [{text, url, callback_data}] в формате NewsletterButton.
    buttons: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # SET NULL: удаление файла не должно ломать правило (текст останется).
    file_id: Mapped[int | None] = mapped_column(
        ForeignKey("file.id", ondelete="SET NULL"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=true()
    )

    __table_args__ = (
        CheckConstraint("days_offset >= 0", name="ck_dripnewsletter_days_offset"),
        Index("ix_dripnewsletter_active_state", "is_active", "trigger_state"),
    )


class DripNewsletterSend(Base, TimestampMixin):
    """
    Лог отправок капельной рассылки — гарантия «один раз на (правило, юзер)».

    Строка вставляется в ОДНОЙ транзакции с outbox-сообщением (claim через
    INSERT ... ON CONFLICT DO NOTHING RETURNING), поэтому конкурентные запуски
    sweep не могут отправить одному пользователю дубль.
    """

    drip_newsletter_id: Mapped[int] = mapped_column(
        ForeignKey("dripnewsletter.id", ondelete="CASCADE"), nullable=False
    )
    telegram_user_id: Mapped[int] = mapped_column(
        ForeignKey("telegramuser.id", ondelete="CASCADE"), nullable=False
    )
    # Трассировка к логам бота и Redis-ключам идемпотентности.
    broadcast_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "drip_newsletter_id", "telegram_user_id", name="uq_dripsend_rule_user"
        ),
    )
