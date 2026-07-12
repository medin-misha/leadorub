from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.system import Base, TimestampMixin


class OutboxMessage(Base, TimestampMixin):
    """RMQ-событие, которое публикуется только после commit бизнес-транзакции."""

    __tablename__ = "rmq_outbox_message"
    __table_args__ = (
        Index("ix_rmq_outbox_dispatch", "status", "available_at", "id"),
        Index("ix_rmq_outbox_locked_until", "locked_until"),
    )

    message_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    event: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    exchange_name: Mapped[str] = mapped_column(String(255), nullable=False)
    exchange_type: Mapped[str] = mapped_column(String(32), nullable=False)
    routing_key: Mapped[str] = mapped_column(String(255), nullable=False)
    queue_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    correlation_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
