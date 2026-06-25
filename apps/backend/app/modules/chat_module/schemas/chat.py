from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class SupportMessageRMQ(BaseModel):
    """payload входящего ТЕКСТОВОГО сообщения поддержки (бот → RMQ → backend).

    Совпадает с тем, что публикует support_module бота в очередь
    `telegram_support_in`. Медиа едут отдельным путём (HTTP multipart на
    `POST /chat/inbound-media`), т.к. бинарь через RMQ гонять не стоит.
    """

    telegram_id: int
    text: str
    tg_message_id: int | None = None


class ChatMessageCreate(BaseModel):
    """Внутренняя схема для CRUD.create(ChatMessage)."""

    telegram_user_id: int
    direction: Literal["user", "admin"]
    text: str | None = None
    tg_message_id: int | None = None
    file_id: int | None = None
    is_read: bool = False


class ChatMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    telegram_user_id: int
    direction: str
    text: str | None
    tg_message_id: int | None
    file_id: int | None
    file_name: str | None
    is_read: bool
    created_at: datetime


class ConversationRead(BaseModel):
    """Строка списка диалогов: пользователь + сводка последнего сообщения."""

    telegram_user_id: int
    telegram_id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    last_text: str | None
    last_at: datetime | None
    last_direction: str | None
    unread_count: int
