import unittest

from app.modules.notification_module.services.idempotency import IdempotencyStore


class _FakeRedis:
    """Мини-фейк Redis: SET NX EX через локальный dict."""

    def __init__(self) -> None:
        self.store: dict = {}

    async def set(self, key, value, nx=False, ex=None):
        if nx and key in self.store:
            return None  # NX: ключ уже есть → не поставили
        self.store[key] = value
        return True

    async def ping(self):
        return True

    async def aclose(self):
        pass


class IdempotencyStoreClaimTests(unittest.IsolatedAsyncioTestCase):
    async def test_claim_first_true_second_false(self) -> None:
        store = IdempotencyStore()
        store._redis = _FakeRedis()  # обходим connect: подставляем фейк
        store._ttl = 100
        self.assertTrue(await store.claim("bcast-1", 111))  # первый — шлём
        self.assertFalse(await store.claim("bcast-1", 111))  # повтор — пропускаем
        self.assertTrue(await store.claim("bcast-1", 222))  # другой chat_id — шлём

    async def test_claim_degrades_without_broadcast_id(self) -> None:
        store = IdempotencyStore()
        store._redis = _FakeRedis()
        store._ttl = 100
        # Нет broadcast_id (старое сообщение) → дедуп выключен, всегда True.
        self.assertTrue(await store.claim(None, 111))
        self.assertTrue(await store.claim(None, 111))

    async def test_claim_degrades_when_redis_unavailable(self) -> None:
        store = IdempotencyStore()
        store._redis = None  # Redis не подключён
        store._ttl = 100
        self.assertTrue(await store.claim("bcast-1", 111))

    async def test_claim_degrades_on_redis_error(self) -> None:
        class _BoomRedis(_FakeRedis):
            async def set(self, *a, **k):
                raise RuntimeError("redis down")

        store = IdempotencyStore()
        store._redis = _BoomRedis()
        store._ttl = 100
        # Ошибка Redis в рантайме → degrade, шлём (True), не роняем рассылку.
        self.assertTrue(await store.claim("bcast-1", 111))
