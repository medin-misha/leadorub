"""
In-memory cache auth-сессий Telegram-пользователей.

Системный модуль хранит факт успешной аутентификации и backend payload в памяти
процесса. Это даёт быстрый доступ для защищённых хендлеров и не требует
отдельного хранилища на уровне шаблона.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.modules.system.config import system_settings
from app.modules.system.schemas import TelegramUserRead


@dataclass(slots=True)
class AuthSession:
    """Кешируемая auth-сессия Telegram-пользователя."""

    telegram_id: int
    telegram_user: TelegramUserRead
    authenticated: bool = True
    authenticated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class InMemoryAuthCache:
    """Простой bounded in-memory cache с вытеснением самых старых записей."""

    def __init__(self, max_size: int) -> None:
        self._max_size = max_size
        self._storage: OrderedDict[int, AuthSession] = OrderedDict()

    def get(self, telegram_id: int) -> AuthSession | None:
        """Возвращает сессию пользователя и обновляет её LRU-позицию."""

        session = self._storage.get(telegram_id)
        if session is None:
            return None

        self._storage.move_to_end(telegram_id)
        return session

    def set(self, session: AuthSession) -> None:
        """Сохраняет auth-сессию, ограничивая размер кеша."""

        self._storage[session.telegram_id] = session
        self._storage.move_to_end(session.telegram_id)

        while len(self._storage) > self._max_size:
            self._storage.popitem(last=False)

    def clear(self) -> None:
        """Полностью очищает auth-кеш процесса."""

        self._storage.clear()

    def size(self) -> int:
        """Возвращает количество записей в кеше."""

        return len(self._storage)


auth_cache = InMemoryAuthCache(max_size=system_settings.auth_cache_max_size)
