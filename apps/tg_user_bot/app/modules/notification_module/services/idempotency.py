"""Идемпотентность рассылки через Redis с двухфазным маркером.

Короткий ``processing``-маркер защищает от параллельной отправки, а ``sent``
ставится только после успешной или заведомо невозможной доставки. При временной
ошибке processing снимается, поэтому повторная доставка RMQ может попробовать снова.
"""

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import uuid4

from redis.asyncio import Redis, from_url

if TYPE_CHECKING:
    from app.core.config import MainSettings

logger = logging.getLogger(__name__)

KEY_PREFIX = "newsletter"
PROCESSING_TTL_SECONDS = 900

_COMPLETE_SCRIPT = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('set', KEYS[1], 'sent', 'EX', ARGV[2])
end
return 0
"""

_RELEASE_SCRIPT = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
end
return 0
"""


@dataclass(frozen=True, slots=True)
class IdempotencyClaim:
    """Право конкретного worker-а завершить или освободить отправку."""

    key: str | None
    token: str | None


class IdempotencyStore:
    """Redis-хранилище состояний доставки получателю в рамках рассылки."""

    def __init__(self) -> None:
        self._redis: Redis | None = None
        self._ttl: int = 172800

    async def connect(self, settings: "MainSettings") -> None:
        """Подключается к Redis; при недоступности работает без дедупликации."""
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

    async def claim(
        self, broadcast_id: str | None, chat_id: int | str
    ) -> IdempotencyClaim | None:
        """Возвращает claim для отправки или ``None``, если адресат уже занят/готов."""
        if broadcast_id is None or self._redis is None:
            return IdempotencyClaim(key=None, token=None)

        key = f"{KEY_PREFIX}:{broadcast_id}:{chat_id}"
        token = f"processing:{uuid4()}"
        try:
            was_set = await self._redis.set(
                key, token, nx=True, ex=PROCESSING_TTL_SECONDS
            )
            return IdempotencyClaim(key=key, token=token) if was_set else None
        except Exception:
            logger.warning(
                "[idempotency] ошибка Redis при claim chat_id=%s — degrade",
                chat_id,
                exc_info=True,
            )
            return IdempotencyClaim(key=None, token=None)

    async def complete(self, claim: IdempotencyClaim) -> None:
        """Атомарно заменяет принадлежащий worker-у processing на долгий sent."""
        if claim.key is None or claim.token is None or self._redis is None:
            return
        try:
            await self._redis.eval(
                _COMPLETE_SCRIPT, 1, claim.key, claim.token, self._ttl
            )
        except Exception:
            logger.warning(
                "[idempotency] не удалось зафиксировать доставку key=%s",
                claim.key,
                exc_info=True,
            )

    async def release(self, claim: IdempotencyClaim) -> None:
        """Снимает только собственный processing после временной ошибки."""
        if claim.key is None or claim.token is None or self._redis is None:
            return
        try:
            await self._redis.eval(_RELEASE_SCRIPT, 1, claim.key, claim.token)
        except Exception:
            logger.warning(
                "[idempotency] не удалось освободить claim key=%s",
                claim.key,
                exc_info=True,
            )


idempotency_store = IdempotencyStore()
