"""Идемпотентность рассылки через Redis.

Стратегия claim-before-send: перед отправкой каждому получателю ставим маркер
`SET newsletter:{broadcast_id}:{chat_id} 1 NX EX <ttl>`. Если поставили (ключа
не было) — мы первые, шлём. Если ключ уже есть — уже слали, пропускаем. Маркер
НЕ удаляется: он переживает рассылку и при редоставке чанка не даёт отправить
повторно. Чистит его TTL.

Degrade: если broadcast_id нет (старое сообщение) или Redis недоступен/упал —
claim возвращает True (шлём без дедупа). Доставка приоритетнее дедупа.
"""

import logging
from typing import TYPE_CHECKING

from redis.asyncio import Redis, from_url

if TYPE_CHECKING:
    from app.core.config import MainSettings

logger = logging.getLogger(__name__)

# Префикс отделяет маркеры рассылки от прочих ключей в той же БД Redis.
KEY_PREFIX = "newsletter"


class IdempotencyStore:
    """Redis-хранилище маркеров «кому уже отправили» в рамках одной рассылки."""

    def __init__(self) -> None:
        self._redis: Redis | None = None
        self._ttl: int = 172800

    async def connect(self, settings: "MainSettings") -> None:
        """Подключается к Redis на старте бота. Best-effort: при ошибке/отсутствии
        конфига остаёмся в degrade (claim всегда True)."""
        self._ttl = settings.newsletter_idempotency_ttl_seconds
        if not settings.redis_url:
            logger.warning(
                "[idempotency] redis_url не задан — рассылка пойдёт без дедупа"
            )
            return
        try:
            self._redis = from_url(settings.redis_url, decode_responses=True)
            await self._redis.ping()
            logger.info("[idempotency] Redis подключён, дедуп рассылки активен")
        except Exception:
            logger.warning(
                "[idempotency] Redis недоступен на старте — degrade (без дедупа)",
                exc_info=True,
            )
            self._redis = None

    async def close(self) -> None:
        """Закрывает соединение с Redis при остановке бота."""
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None

    async def claim(self, broadcast_id: str | None, chat_id: int | str) -> bool:
        """Пытается застолбить отправку. True = слать, False = пропустить (уже слали).

        degrade → True: нет broadcast_id (старое сообщение) или Redis недоступен.
        """
        if broadcast_id is None or self._redis is None:
            return True
        key = f"{KEY_PREFIX}:{broadcast_id}:{chat_id}"
        try:
            # SET ... NX EX: вернёт True если поставили, None если ключ уже был.
            was_set = await self._redis.set(key, 1, nx=True, ex=self._ttl)
            return bool(was_set)
        except Exception:
            logger.warning(
                "[idempotency] ошибка Redis при claim chat_id=%s — degrade",
                chat_id,
                exc_info=True,
            )
            return True


# Модульный синглтон: создаётся при импорте, подключается в lifecycle.
idempotency_store = IdempotencyStore()
