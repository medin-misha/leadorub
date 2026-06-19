"""Auth-layer системного Telegram-модуля."""

from .decorators import login_required
from .service import ensure_authenticated, get_cached_auth_session

__all__ = [
    "ensure_authenticated",
    "get_cached_auth_session",
    "login_required",
]
