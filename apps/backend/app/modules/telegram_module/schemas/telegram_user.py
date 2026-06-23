from datetime import datetime

from pydantic import BaseModel, ConfigDict

from .user_profile import UserProfileRead, UserProfileRegister
from .user_stats import UserStatsRead, UserStatsRegister


class TelegramUserBase(BaseModel):
    telegram_id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    is_blocket_bot: bool = False
    language_code: str | None = None


class TelegramUserCreate(TelegramUserBase):
    pass


class TelegramUserRegister(BaseModel):
    """
    Композитный DTO регистрации: атомарно создаёт TelegramUser + UserProfile + UserStats.

    `telegram_user` обязателен (идентичность из Telegram), `profile` и `stats`
    необязательны — при отсутствии связанные сущности создаются с дефолтами.
    """

    telegram_user: TelegramUserCreate
    profile: UserProfileRegister | None = None
    stats: UserStatsRegister | None = None


class TelegramUserLogin(BaseModel):
    telegram_id: int


class TelegramUserPatch(BaseModel):
    telegram_id: int | None = None
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    is_blocket_bot: bool | None = None
    language_code: str | None = None


class TelegramUserRead(TelegramUserBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime
    user_profile: UserProfileRead | None = None
    user_stats: UserStatsRead | None = None
