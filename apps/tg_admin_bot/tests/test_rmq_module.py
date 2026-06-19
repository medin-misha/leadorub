import unittest

from app.modules.rmq_module import RMQConfigurationError
from app.modules.rmq_module.config import rmq_settings
from app.modules.rmq_module.schemas import RMQMessage
from app.modules.rmq_module.services.client import RMQClient
from app.modules.rmq_module.services.publisher import RMQPublisher
from app.modules.rmq_module.services.registry import RMQConsumerRegistry
from app.modules.rmq_module.services.runtime import RMQRuntime


class _FakeClient:
    def __init__(self) -> None:
        self.connected = False
        self.connect_calls = 0
        self.ensure_topology_calls: list[tuple] = []
        self.declare_exchange_calls: list[tuple] = []
        self.publish_calls: list[dict] = []
        self.closed = False

    async def connect(self) -> None:
        self.connect_calls += 1
        self.connected = True

    async def ensure_topology(self, exchange, queue=None):
        self.connected = True
        self.ensure_topology_calls.append((exchange, queue))
        return None

    async def declare_exchange(self, exchange):
        self.connected = True
        self.declare_exchange_calls.append(exchange)
        return None

    async def publish(self, **kwargs):
        self.publish_calls.append(kwargs)

    async def consume(self, *, queue_name, callback) -> None:
        _ = queue_name
        _ = callback

    async def close(self) -> None:
        self.connected = False
        self.closed = True


async def _noop_handler(message: RMQMessage) -> None:
    _ = message


async def _other_handler(message: RMQMessage) -> None:
    _ = message


class RMQConsumerRegistryTests(unittest.TestCase):
    def test_register_keeps_single_entry_for_identical_registration(self) -> None:
        registry = RMQConsumerRegistry()

        first = registry.register(
            queue_name="queue.a",
            exchange_name="app.events",
            routing_key="queue.a",
            handler=_noop_handler,
        )
        second = registry.register(
            queue_name="queue.a",
            exchange_name="app.events",
            routing_key="queue.a",
            handler=_noop_handler,
        )

        self.assertEqual(first, second)
        self.assertEqual(len(registry.registrations()), 1)

    def test_register_rejects_duplicate_topology_for_different_handler(self) -> None:
        registry = RMQConsumerRegistry()
        registry.register(
            queue_name="queue.a",
            exchange_name="app.events",
            routing_key="queue.a",
            handler=_noop_handler,
        )

        with self.assertRaises(ValueError):
            registry.register(
                queue_name="queue.a",
                exchange_name="app.events",
                routing_key="queue.a",
                handler=_other_handler,
            )


class RMQPublisherTests(unittest.IsolatedAsyncioTestCase):
    async def test_publish_declares_queue_when_queue_name_provided(self) -> None:
        client = _FakeClient()
        publisher = RMQPublisher(client=client)

        message = await publisher.publish(
            event="telegram.user.created",
            payload={"telegram_id": 1},
            queue_name="telegram.user.created",
        )

        self.assertEqual(message.event, "telegram.user.created")
        self.assertEqual(message.payload["telegram_id"], 1)
        self.assertEqual(len(client.ensure_topology_calls), 1)
        self.assertEqual(len(client.publish_calls), 1)


class RMQRuntimeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._original_amqp_url = rmq_settings.amqp_url
        self._original_consumer_enabled = rmq_settings.rabbitmq_consumer_enabled

    def tearDown(self) -> None:
        rmq_settings.amqp_url = self._original_amqp_url
        rmq_settings.rabbitmq_consumer_enabled = self._original_consumer_enabled

    async def test_runtime_start_and_stop_manage_state(self) -> None:
        client = _FakeClient()
        registry = RMQConsumerRegistry()
        runtime = RMQRuntime(client=client, registry=registry)

        registry.register(
            queue_name="queue.a",
            exchange_name="app.events",
            routing_key="queue.a",
            handler=_noop_handler,
        )
        await runtime.start()
        description = runtime.describe()

        self.assertTrue(description["started"])
        self.assertTrue(client.connected)
        self.assertEqual(client.connect_calls, 1)
        self.assertEqual(description["listener_count"], 1)

        await runtime.stop()

        self.assertFalse(runtime.describe()["started"])
        self.assertTrue(client.closed)

    async def test_runtime_start_is_skipped_without_registrations(self) -> None:
        rmq_settings.amqp_url = None
        client = _FakeClient()
        registry = RMQConsumerRegistry()
        runtime = RMQRuntime(client=client, registry=registry)

        await runtime.start()

        self.assertFalse(runtime.describe()["started"])
        self.assertFalse(client.connected)
        self.assertEqual(client.connect_calls, 0)

    async def test_runtime_start_requires_amqp_url_when_consumer_registered(
        self,
    ) -> None:
        rmq_settings.amqp_url = None
        runtime = RMQRuntime(
            client=RMQClient(settings=rmq_settings), registry=RMQConsumerRegistry()
        )
        runtime._registry.register(
            queue_name="queue.a",
            exchange_name="app.events",
            routing_key="queue.a",
            handler=_noop_handler,
        )

        with self.assertRaises(RMQConfigurationError):
            await runtime.start()
