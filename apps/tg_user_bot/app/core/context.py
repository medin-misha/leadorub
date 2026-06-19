"""
Runtime-context для данных текущего update.

Сейчас через этот файл системный модуль прокидывает auth-сессию в код
хендлеров без ручной передачи аргументов и без глобального состояния,
привязанного к конкретному coroutine execution flow.
"""

from __future__ import annotations

from contextvars import ContextVar, Token
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.system.auth.cache import AuthSession


_current_auth_session: ContextVar["AuthSession | None"] = ContextVar(
    "current_auth_session",
    default=None,
)


def set_current_auth_session(session: "AuthSession") -> Token["AuthSession | None"]:
    """Сохраняет auth-сессию на время обработки текущего update."""

    return _current_auth_session.set(session)


def reset_current_auth_session(token: Token["AuthSession | None"]) -> None:
    """Очищает временную auth-сессию после завершения хендлера."""

    _current_auth_session.reset(token)


def get_current_auth_session() -> "AuthSession | None":
    """Возвращает auth-сессию текущего update, если декоратор её уже установил."""

    return _current_auth_session.get()
