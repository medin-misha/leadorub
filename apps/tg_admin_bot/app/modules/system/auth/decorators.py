"""
Декораторы доступа для Telegram-хендлеров.

Системный модуль предоставляет `login_required` как базовый механизм защиты
хендлеров. Декоратор сам поднимает auth-сессию через backend и делает её
доступной в `app.core.context` на время обработки update.
"""

from __future__ import annotations

import logging
from functools import wraps
from typing import Any, Awaitable, Callable, TypeVar, cast

from aiogram.types import CallbackQuery, Message, TelegramObject

from app.core.context import reset_current_auth_session, set_current_auth_session
from app.modules.system.client import (
    BackendClientError,
    BackendNotConfiguredError,
    BackendUnavailableError,
    BackendUnexpectedResponseError,
)
from app.modules.system.messages import get_messages

from .service import AuthenticationFlowError, ensure_authenticated

logger = logging.getLogger(__name__)

Handler = TypeVar("Handler", bound=Callable[..., Awaitable[Any]])


def login_required(
    handler: Handler | None = None,
    *,
    no_cache: bool = False,
) -> Handler | Callable[[Handler], Handler]:
    """Пускает хендлер дальше только после успешной backend-аутентификации."""

    def decorator(target_handler: Handler) -> Handler:
        @wraps(target_handler)
        async def wrapper(event: TelegramObject, *args: Any, **kwargs: Any) -> Any:
            messages = get_messages()
            telegram_user = getattr(event, "from_user", None)
            if telegram_user is None:
                await _answer_event(event, messages["auth_missing_user"])
                return None

            try:
                session = await ensure_authenticated(
                    telegram_user=telegram_user,
                    no_cache=no_cache,
                )
            except BackendNotConfiguredError:
                await _answer_event(event, messages["auth_backend_not_configured"])
                return None
            except BackendUnavailableError:
                logger.exception("Backend is unavailable during auth flow.")
                await _answer_event(event, messages["auth_backend_unavailable"])
                return None
            except BackendUnexpectedResponseError:
                logger.exception(
                    "Backend returned unexpected response during auth flow."
                )
                await _answer_event(event, messages["auth_backend_unexpected_response"])
                return None
            except BackendClientError:
                logger.exception("Unhandled backend client error escaped auth flow.")
                await _answer_event(event, messages["auth_backend_unexpected_response"])
                return None
            except AuthenticationFlowError:
                logger.exception("Authentication flow failed unexpectedly.")
                await _answer_event(event, messages["auth_failed"])
                return None

            token = set_current_auth_session(session)
            try:
                return await target_handler(event, *args, **kwargs)
            finally:
                reset_current_auth_session(token)

        return cast(Handler, wrapper)

    if handler is not None:
        return decorator(handler)

    return decorator


async def _answer_event(event: TelegramObject, text: str) -> None:
    """Отвечает на update вне зависимости от того, это message или callback."""

    if isinstance(event, Message):
        await event.answer(text)
        return

    if isinstance(event, CallbackQuery):
        await event.answer(text, show_alert=True)
        return

    answer = getattr(event, "answer", None)
    if callable(answer):
        await answer(text)
