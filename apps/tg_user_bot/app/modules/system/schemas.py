"""
Локальные Pydantic-схемы системного Telegram-модуля.

Системный модуль использует эти схемы как контракт с backend API, не импортируя
напрямую код из `fastapi_template`. Это снижает связность между двумя
шаблонами и позволяет развивать bot/runtime отдельно от backend-репозитория.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserProfileRead(BaseModel):
    """Минимальная read-схема профиля пользователя из backend."""

    model_config = ConfigDict(extra="ignore")

    id: int
    telegram_user_id: int
    phone: str | None = None
    email: str | None = None
    timezone: str | None = None
    full_name: str | None = None
    note: str | None = None
    created_at: datetime
    updated_at: datetime


class UserStatsRead(BaseModel):
    """Минимальная read-схема статистики пользователя из backend."""

    model_config = ConfigDict(extra="ignore")

    id: int
    telegram_user_id: int
    last_seen_at: datetime | None = None
    source: str | None = None
    state: str | None = None
    created_at: datetime
    updated_at: datetime


class TelegramUserLoginPayload(BaseModel):
    """Payload для запроса логина пользователя через backend."""

    telegram_id: int


class UserStatePayload(BaseModel):
    """Payload сервисного обновления состояния диалога (`PUT /telegram/state`)."""

    telegram_id: int
    state: str | None = None


class TelegramUserIdentityCreate(BaseModel):
    """Identity-часть composite payload регистрации (`telegram_user`)."""

    telegram_id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    is_blocket_bot: bool = False
    language_code: str | None = None


class TelegramUserStatsCreate(BaseModel):
    """Опциональная stats-часть composite payload регистрации (`stats`)."""

    source: str | None = None
    state: str | None = None


class TelegramUserProfileCreate(BaseModel):
    """Опциональная profile-часть composite payload регистрации (`profile`)."""

    phone: str | None = None
    email: str | None = None
    timezone: str | None = None
    full_name: str | None = None
    note: str | None = None


class TelegramUserCreatePayload(BaseModel):
    """Composite payload для регистрации Telegram-пользователя через backend.

    Backend ожидает вложенную структуру `{telegram_user, profile?, stats?}`.
    `telegram_user` обязателен; `profile` и `stats` опциональны и опускаются,
    если у бота нет соответствующих данных (см. `exclude_none` в client.py).
    """

    telegram_user: TelegramUserIdentityCreate
    profile: TelegramUserProfileCreate | None = None
    stats: TelegramUserStatsCreate | None = None


class TelegramUserRead(BaseModel):
    """Ответ backend с данными Telegram-пользователя, профиля и статистики."""

    model_config = ConfigDict(extra="ignore")

    id: int
    telegram_id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    is_blocket_bot: bool = False
    language_code: str | None = None
    created_at: datetime
    updated_at: datetime
    user_profile: UserProfileRead | None = None
    user_stats: UserStatsRead | None = None


class RequisitionCreatePayload(BaseModel):
    """Payload для создания новой заявки через backend."""

    telegram_id: int
    type: str
    payload: dict


class RequisitionRead(BaseModel):
    """Схема чтения данных заявки, возвращаемых backend."""

    model_config = ConfigDict(extra="ignore")

    id: int
    telegram_user_id: int
    type: str
    status: str
    payload: dict
    admin_comment: str | None = None
    created_at: datetime
    updated_at: datetime
