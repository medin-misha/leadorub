"""
Системные Telegram-хендлеры шаблона.

Этот файл содержит только обязательные команды platform-layer: проверку
доступности бота, introspection для debug-сценариев и команды, связанные с
базовой auth-системой, на которую могут опираться остальные Telegram-модули.
"""

from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.core import settings
from app.core.context import get_current_auth_session
from app.modules.system.auth import (
    ensure_authenticated,
    get_cached_auth_session,
    login_required,
)
from app.modules.system.auth.cache import auth_cache
from app.modules.system.auth.service import AuthenticationFlowError
from app.modules.system.client import BackendClientError
from app.modules.system.config import system_settings
from app.modules.system.deep_link import parse_source
from app.modules.system.messages import get_messages
from app.modules.psychologist.keyboards import get_main_menu_keyboard
from app.modules.psychologist.messages import get_messages as get_psy_messages

logger = logging.getLogger(__name__)

router = Router(name="system")
_MESSAGES = get_messages()
_PSY_MESSAGES = get_psy_messages()


@router.message(Command("start"))
async def start_command(
    message: Message, command: CommandObject, state: FSMContext
) -> None:
    """Подтверждает, что бот жив, и фиксирует source из deep-link payload.

    Telegram прокидывает `?start=<payload>` как `command.args`. По префиксной
    схеме `source_<value>` бот извлекает маркетинговый источник и регистрирует
    пользователя сразу здесь — source живёт только в этом сообщении, поэтому
    откладывать провижининг до первого `@login_required` нельзя (потеряем
    first-touch атрибуцию).
    """

    # /start сбрасывает любой активный режим (в т.ч. режим поддержки): для
    # пользователя это «вернуться в начало», поэтому состояние FSM очищаем.
    await state.clear()

    # Источник важен только при первом контакте; для уже известных пользователей
    # backend вернёт login 200 и source будет проигнорирован.
    source = parse_source(command.args)
    await _provision_on_start(message, source)

    await message.answer(
        text=_PSY_MESSAGES["welcome"],
        reply_markup=get_main_menu_keyboard(),
    )


async def _provision_on_start(message: Message, source: str | None) -> None:
    """Регистрирует пользователя на /start, не роняя ответ при сбое backend.

    Повторяет стратегию `login_required`: ошибки backend логируются и
    проглатываются, чтобы бот всё равно отправил приветствие. Полноценный
    auth-flow всё равно отработает позже на первом защищённом хендлере.
    """

    telegram_user = message.from_user
    if telegram_user is None:
        return

    try:
        await ensure_authenticated(telegram_user=telegram_user, source=source)
    except (BackendClientError, AuthenticationFlowError):
        logger.warning(
            "Provisioning on /start failed for user %s (source=%s); "
            "deferring to login_required flow.",
            telegram_user.id,
            source,
            exc_info=True,
        )


@router.message(Command("authstatus"))
@login_required(no_cache=True)
async def auth_status_command(message: Message) -> None:
    """Показывает текущую auth-сессию пользователя из in-memory cache."""

    auth_session = get_current_auth_session()
    if auth_session is None:
        await message.answer(_MESSAGES["auth_status_missing_context"])
        return

    telegram_user = auth_session.telegram_user
    username = (
        f"@{telegram_user.username}" if telegram_user.username else "без username"
    )
    profile_state = "есть" if telegram_user.user_profile else "нет"

    await message.answer(
        _MESSAGES["auth_status"].format(
            telegram_id=auth_session.telegram_id,
            backend_user_id=telegram_user.id,
            username=username,
            authenticated_at=auth_session.authenticated_at.isoformat(),
            cache_size=auth_cache.size(),
            profile_state=profile_state,
        )
    )


@router.message(Command("usersysinfo"))
async def user_system_info_command(message: Message) -> None:
    """Показывает техническую системную информацию, когда проект запущен в debug."""

    if not system_settings.debug_commands_enabled:
        await message.answer(_MESSAGES["user_sys_info_disabled"])
        return

    user = message.from_user
    if user is None:
        await message.answer(_MESSAGES["auth_missing_user"])
        return

    username = f"@{user.username}" if user.username else "без username"
    cached_session = get_cached_auth_session(user.id)
    cache_state = "authenticated" if cached_session else "not authenticated"

    await message.answer(
        _MESSAGES["user_sys_info"].format(
            username=username,
            user_id=user.id,
            chat_id=message.chat.id,
            first_name=user.first_name or "—",
            last_name=user.last_name or "—",
            language_code=user.language_code or "—",
            cache_state=cache_state,
            backend_url=settings.backend_url or "—",
        )
    )
