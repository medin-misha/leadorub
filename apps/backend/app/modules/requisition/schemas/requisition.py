from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.modules.telegram_module.schemas.telegram_user import TelegramUserRead


class RequisitionCreate(BaseModel):
    """Схема для создания новой заявки от бота."""

    telegram_id: int = Field(..., description="ID пользователя в Telegram")
    type: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Тип продукта/заявки (например, 'consultation', 'community')",
    )
    payload: dict[str, Any] = Field(
        default_factory=dict, description="Произвольные данные полей заявки"
    )


class RequisitionStatusUpdate(BaseModel):
    """Схема для обновления статуса заявки администратором."""

    status: str = Field(
        ...,
        min_length=1,
        max_length=30,
        description="Новый статус заявки: 'pending', 'in_progress', 'approved', 'rejected'",
    )
    admin_comment: str | None = Field(
        default=None, max_length=1024, description="Комментарий администратора"
    )


class RequisitionRead(BaseModel):
    """Схема для чтения данных заявки."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    telegram_user_id: int
    type: str
    status: str
    payload: dict[str, Any]
    admin_comment: str | None
    created_at: datetime
    updated_at: datetime

    # Вложенный пользователь Telegram
    telegram_user: TelegramUserRead | None = None
