import json
from collections.abc import Awaitable, Callable
from logging import getLogger
from typing import Any

from aio_pika import DeliveryMode, ExchangeType, Message, connect_robust
from aio_pika.abc import (
    AbstractIncomingMessage,
    AbstractQueue,
    AbstractRobustChannel,
    AbstractRobustConnection,
)

from app.modules.rmq_module.config import rmq_settings
from app.modules.rmq_module.exceptions import RMQConfigurationError

from .topology import ExchangeSpec, QueueSpec

logger = getLogger(__name__)


class RMQClient:
    def __init__(self, amqp_url: str | None) -> None:
        self._amqp_url = amqp_url
        self._connection: AbstractRobustConnection | None = None
        self._channel: AbstractRobustChannel | None = None

    @property
    def connected(self) -> bool:
        return bool(
            self._connection is not None
            and not self._connection.is_closed
            and self._channel is not None
            and not self._channel.is_closed
        )

    async def connect(self) -> None:
        if self.connected:
            return

        if not self._amqp_url:
            raise RMQConfigurationError(
                "RabbitMQ is not configured. Set amqp_url or disable the RMQ module."
            )

        self._connection = await connect_robust(self._amqp_url)
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=rmq_settings.prefetch_count)
        logger.info("RabbitMQ connection established")

    async def close(self) -> None:
        if self._channel is not None and not self._channel.is_closed:
            await self._channel.close()
        if self._connection is not None and not self._connection.is_closed:
            await self._connection.close()
        self._channel = None
        self._connection = None

    async def _get_channel(self) -> AbstractRobustChannel:
        await self.connect()
        if self._channel is None:
            raise RuntimeError("RabbitMQ channel was not created")
        return self._channel

    async def declare_exchange(self, spec: ExchangeSpec):
        channel = await self._get_channel()
        return await channel.declare_exchange(
            name=spec.name,
            type=ExchangeType(spec.exchange_type),
            durable=spec.durable,
            auto_delete=spec.auto_delete,
        )

    async def declare_queue(self, spec: QueueSpec) -> AbstractQueue:
        channel = await self._get_channel()
        return await channel.declare_queue(
            name=spec.name,
            durable=spec.durable,
            auto_delete=spec.auto_delete,
        )

    async def ensure_topology(
        self, exchange: ExchangeSpec, queue: QueueSpec | None = None
    ) -> AbstractQueue | None:
        declared_exchange = await self.declare_exchange(exchange)
        if queue is None:
            return None

        declared_queue = await self.declare_queue(queue)
        routing_key = queue.routing_key or queue.name
        await declared_queue.bind(declared_exchange, routing_key=routing_key)
        return declared_queue

    async def publish(
        self,
        *,
        body: dict[str, Any],
        exchange_name: str,
        exchange_type: str,
        routing_key: str,
        message_id: str,
        correlation_id: str | None,
        event_name: str,
        source: str,
    ) -> None:
        exchange = await self.declare_exchange(
            ExchangeSpec(name=exchange_name, exchange_type=exchange_type)
        )
        message = Message(
            body=json.dumps(body).encode("utf-8"),
            content_type="application/json",
            delivery_mode=DeliveryMode.PERSISTENT,
            message_id=message_id,
            correlation_id=correlation_id,
            type=event_name,
            app_id=source,
        )
        await exchange.publish(
            message=message,
            routing_key=routing_key,
            timeout=rmq_settings.publish_timeout,
        )

    async def get_message(self, *, queue_name: str) -> AbstractIncomingMessage | None:
        queue = await self.declare_queue(QueueSpec(name=queue_name))
        return await queue.get(fail=False)

    async def consume(
        self,
        *,
        queue_name: str,
        callback: Callable[[AbstractIncomingMessage], Awaitable[None]],
    ) -> None:
        queue = await self.declare_queue(QueueSpec(name=queue_name))
        await queue.consume(callback)


rmq_client = RMQClient(amqp_url=rmq_settings.amqp_url)
