from .drip import (
    DripNewsletterCreate,
    DripNewsletterPatch,
    DripNewsletterRead,
)
from .newsletter import (
    NewsletterButton,
    NewsletterContent,
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
    UserStateUpdate,
    UserStatsCreate,
    UserStatsPatch,
    UserStatsRead,
    UserStatsRegister,
)

__all__ = [
    "DripNewsletterCreate",
    "DripNewsletterPatch",
    "DripNewsletterRead",
    "NewsletterButton",
    "NewsletterContent",
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
    "UserStateUpdate",
    "UserStatsCreate",
    "UserStatsPatch",
    "UserStatsRead",
    "UserStatsRegister",
]
