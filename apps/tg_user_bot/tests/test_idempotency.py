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

    async def eval(self, script, numkeys, key, *args):
        _ = numkeys
        token = args[0]
        if self.store.get(key) != token:
            return 0
        if "redis.call('set'" in script:
            self.store[key] = "sent"
        else:
            del self.store[key]
        return 1

    async def ping(self):
        return True

    async def aclose(self):
        pass


class IdempotencyStoreClaimTests(unittest.IsolatedAsyncioTestCase):
    async def test_claim_first_true_second_false(self) -> None:
        store = IdempotencyStore()
        store._redis = _FakeRedis()  # обходим connect: подставляем фейк
        store._ttl = 100
        claim = await store.claim("bcast-1", 111)
        self.assertIsNotNone(claim)
        self.assertIsNone(await store.claim("bcast-1", 111))
        self.assertIsNotNone(await store.claim("bcast-1", 222))

    async def test_complete_keeps_recipient_claimed_as_sent(self) -> None:
        store = IdempotencyStore()
        store._redis = _FakeRedis()
        claim = await store.claim("bcast-1", 111)
        self.assertIsNotNone(claim)

        await store.complete(claim)

        self.assertEqual(store._redis.store[claim.key], "sent")
        self.assertIsNone(await store.claim("bcast-1", 111))

    async def test_release_allows_retry_after_temporary_failure(self) -> None:
        store = IdempotencyStore()
        store._redis = _FakeRedis()
        claim = await store.claim("bcast-1", 111)
        self.assertIsNotNone(claim)

        await store.release(claim)

        self.assertIsNotNone(await store.claim("bcast-1", 111))

    async def test_claim_degrades_without_broadcast_id(self) -> None:
        store = IdempotencyStore()
        store._redis = _FakeRedis()
        store._ttl = 100
        # Нет broadcast_id (старое сообщение) → дедуп выключен, всегда True.
        self.assertIsNotNone(await store.claim(None, 111))
        self.assertIsNotNone(await store.claim(None, 111))

    async def test_claim_degrades_when_redis_unavailable(self) -> None:
        store = IdempotencyStore()
        store._redis = None  # Redis не подключён
        store._ttl = 100
        self.assertIsNotNone(await store.claim("bcast-1", 111))

    async def test_claim_degrades_on_redis_error(self) -> None:
        class _BoomRedis(_FakeRedis):
            async def set(self, *a, **k):
                raise RuntimeError("redis down")

        store = IdempotencyStore()
        store._redis = _BoomRedis()
        store._ttl = 100
        # Ошибка Redis в рантайме → degrade, шлём (True), не роняем рассылку.
        self.assertIsNotNone(await store.claim("bcast-1", 111))
