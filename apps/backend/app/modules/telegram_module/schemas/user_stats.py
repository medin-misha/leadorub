from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserStatsBase(BaseModel):
    telegram_user_id: int
    last_seen_at: datetime | None = None
    source: str | None = None
    state: str | None = None


class UserStatsCreate(UserStatsBase):
    pass


class UserStatsRegister(BaseModel):
    """
    Вложенный DTO для регистрации пользователя через композитный эндпоинт.

    Не содержит `telegram_user_id` (выводится из создаваемого TelegramUser)
    и `last_seen_at` (инициализируется сервером моментом регистрации).
    """

    source: str | None = None
    state: str | None = None


class UserStateUpdate(BaseModel):
    """
    Сервисное обновление состояния диалога по telegram_id.

    Используется ботом (X-Service-Token): бот не знает внутренних id
    UserStats, поэтому адресует пользователя его Telegram ID.
    """

    telegram_id: int
    state: str | None = None


class UserStatsPatch(BaseModel):
    telegram_user_id: int | None = None
    last_seen_at: datetime | None = None
    source: str | None = None
    state: str | None = None


class UserStatsRead(UserStatsBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
