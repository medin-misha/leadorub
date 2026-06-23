from .newsletter import (
    NewsletterButton,
    NewsletterFilters,
    NewsletterRequest,
    NewsletterResult,
)
from .telegram_user import (
    TelegramUserCreate,
    TelegramUserLogin,
    TelegramUserPatch,
    TelegramUserRead,
    TelegramUserRegister,
)
from .user_profile import (
    UserProfileCreate,
    UserProfilePatch,
    UserProfileRead,
    UserProfileRegister,
)
from .user_stats import (
    UserStatsCreate,
    UserStatsPatch,
    UserStatsRead,
    UserStatsRegister,
)

__all__ = [
    "NewsletterButton",
    "NewsletterFilters",
    "NewsletterRequest",
    "NewsletterResult",
    "TelegramUserCreate",
    "TelegramUserLogin",
    "TelegramUserPatch",
    "TelegramUserRead",
    "TelegramUserRegister",
    "UserProfileCreate",
    "UserProfilePatch",
    "UserProfileRead",
    "UserProfileRegister",
    "UserStatsCreate",
    "UserStatsPatch",
    "UserStatsRead",
    "UserStatsRegister",
]
