import asyncio
from logging import getLogger

from pydantic import ValidationError

from app.modules.rmq_module.config import rmq_settings
from app.modules.rmq_module.schemas import RMQMessage

from .client import RMQClient, rmq_client
from .consumer import RMQConsumerService
from .registry import RMQConsumerRegistry, rmq_registry
from .topology import ExchangeSpec, QueueSpec

logger = getLogger(__name__)


class RMQRuntime:
    def __init__(self, client: RMQClient, registry: RMQConsumerRegistry) -> None:
        self._client = client
        self._registry = registry
        self._consumer_service = RMQConsumerService(client)
        self._stop_event = asyncio.Event()
        self._tasks: list[asyncio.Task[None]] = []
        self._started = False

    @property
    def started(self) -> bool:
        return self._started

    async def start(self) -> None:
        if self._started:
            return

        await self.ensure_topology()
        self._stop_event = asyncio.Event()
        if rmq_settings.consumer_enabled:
            for registration in self._registry.registrations():
                task = asyncio.create_task(
                    self._consumer_service.run_registration(
                        registration,
                        stop_event=self._stop_event,
                    )
                )
                self._tasks.append(task)
        self._started = True
        logger.info("RMQ runtime started")

    async def stop(self) -> None:
        if not self._started:
            return

        self._stop_event.set()
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        await self._client.close()
        self._started = False
        logger.info("RMQ runtime stopped")

    async def ensure_topology(
        self,
        *,
        exchange_name: str | None = None,
        queue_name: str | None = None,
        routing_key: str | None = None,
        exchange_type: str | None = None,
    ) -> None:
        target_exchange = exchange_name or rmq_settings.default_exchange
        target_queue = queue_name or rmq_settings.default_queue
        target_routing_key = routing_key or rmq_settings.default_routing_key
        target_exchange_type = exchange_type or rmq_settings.default_exchange_type

        await self._client.ensure_topology(
            exchange=ExchangeSpec(
                name=target_exchange,
                exchange_type=target_exchange_type,
            ),
            queue=QueueSpec(
                name=target_queue,
                routing_key=target_routing_key,
            ),
        )

    def describe(self) -> dict[str, str | int | bool]:
        return {
            "enabled": rmq_settings.enabled,
            "configured": rmq_settings.configured,
            "started": self._started,
            "connected": self._client.connected,
            "consumer_enabled": rmq_settings.consumer_enabled,
            "registration_count": len(self._registry.registrations()),
            "listener_count": len(self._tasks),
            "default_exchange": rmq_settings.default_exchange,
            "default_queue": rmq_settings.default_queue,
        }

    def parse_message(self, body: bytes) -> RMQMessage | None:
        try:
            return RMQMessage.model_validate_json(body)
        except ValidationError:
            logger.warning("Unable to parse RabbitMQ message as RMQMessage")
            return None


rmq_runtime = RMQRuntime(client=rmq_client, registry=rmq_registry)
