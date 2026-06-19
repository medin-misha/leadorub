"""
Auth-оркестрация системного Telegram-модуля.

Файл реализует базовый flow аутентификации, завязанный на backend telegram API:
сначала bot пытается залогинить пользователя по `telegram_id`, а если backend
ещё не знает этого пользователя, bot регистрирует его и сразу же повторяет
login, после чего кладёт backend payload в in-memory cache.
"""

from __future__ import annotations

import logging

from aiogram.types import User

from app.modules.system.client import (
    BackendClient,
    BackendClientError,
    BackendUserNotFoundError,
    get_backend_client,
)
from app.modules.system.schemas import (
    TelegramUserCreatePayload,
    TelegramUserIdentityCreate,
    TelegramUserRead,
)

from .cache import AuthSession, auth_cache

logger = logging.getLogger(__name__)


class AuthenticationFlowError(RuntimeError):
    """Login/register flow не завершился успешной auth-сессией."""


def get_cached_auth_session(telegram_id: int) -> AuthSession | None:
    """Возвращает кешированную auth-сессию пользователя, если она существует."""

    return auth_cache.get(telegram_id)


async def ensure_authenticated(
    telegram_user: User, no_cache: bool = False
) -> AuthSession:
    """Гарантирует auth-сессию пользователя через cache и backend API."""

    cached_session = auth_cache.get(telegram_user.id)
    if no_cache:
        cached_session = None
    if cached_session is not None:
        return cached_session

    client = get_backend_client()

    try:
        backend_user = await client.login_telegram_user(telegram_user.id)
    except BackendUserNotFoundError:
        logger.info(
            "Telegram user %s not found; provisioning via backend.", telegram_user.id
        )
        backend_user = await _provision_backend_user(client, telegram_user)
    except BackendClientError:
        raise
    except Exception as exc:
        raise AuthenticationFlowError(
            f"Unexpected authentication failure for user {telegram_user.id}"
        ) from exc
    session = AuthSession(
        telegram_id=telegram_user.id,
        telegram_user=backend_user,
    )
    if not no_cache:
        auth_cache.set(session)
    return session


async def _provision_backend_user(
    client: BackendClient,
    telegram_user: User,
) -> TelegramUserRead:
    """Регистрирует пользователя и повторяет login как единую фазу auth-flow."""

    await client.create_telegram_user(_build_create_payload(telegram_user))

    try:
        return await client.login_telegram_user(telegram_user.id)
    except BackendUserNotFoundError as exc:
        raise AuthenticationFlowError(
            f"Backend did not expose telegram user {telegram_user.id} after provisioning."
        ) from exc


def _build_create_payload(telegram_user: User) -> TelegramUserCreatePayload:
    """Собирает composite payload регистрации из Telegram user объекта aiogram.

    Бот на /start не владеет profile/stats данными, поэтому отправляет только
    обязательную identity-часть `telegram_user`. `last_seen_at` backend проставит
    серверно. `profile`/`stats` опускаются (`exclude_none` в client.py).
    """

    return TelegramUserCreatePayload(
        telegram_user=TelegramUserIdentityCreate(
            telegram_id=telegram_user.id,
            username=telegram_user.username,
            first_name=telegram_user.first_name,
            last_name=telegram_user.last_name,
            is_blocket_bot=telegram_user.is_bot,
            language_code=telegram_user.language_code,
        ),
    )
