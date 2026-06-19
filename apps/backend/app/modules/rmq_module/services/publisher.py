from app.core.config import settings
from app.modules.rmq_module.config import rmq_settings
from app.modules.rmq_module.schemas import RMQMessage

from .client import RMQClient, rmq_client
from .topology import ExchangeSpec, QueueSpec


class RMQPublisher:
    def __init__(self, client: RMQClient) -> None:
        self._client = client
        self.default_exchange_name = rmq_settings.default_exchange
        self.default_exchange_type = rmq_settings.default_exchange_type
        self.default_queue_name = rmq_settings.default_queue
        self.default_routing_key = rmq_settings.default_routing_key

    async def publish(
        self,
        *,
        event: str,
        payload: dict,
        exchange_name: str | None = None,
        routing_key: str | None = None,
        queue_name: str | None = None,
        source: str | None = None,
        correlation_id: str | None = None,
        exchange_type: str | None = None,
    ) -> RMQMessage:
        target_exchange = exchange_name or self.default_exchange_name
        target_exchange_type = exchange_type or self.default_exchange_type
        target_queue = queue_name
        target_routing_key = routing_key or queue_name or self.default_routing_key
        message = RMQMessage(
            event=event,
            payload=payload,
            source=source or settings.project_name,
            correlation_id=correlation_id,
        )

        if target_queue is not None:
            await self._client.ensure_topology(
                exchange=ExchangeSpec(
                    name=target_exchange,
                    exchange_type=target_exchange_type,
                ),
                queue=QueueSpec(name=target_queue, routing_key=target_routing_key),
            )
        else:
            await self._client.declare_exchange(
                ExchangeSpec(
                    name=target_exchange,
                    exchange_type=target_exchange_type,
                )
            )

        await self._client.publish(
            body=message.model_dump(mode="json"),
            exchange_name=target_exchange,
            exchange_type=target_exchange_type,
            routing_key=target_routing_key,
            message_id=message.message_id,
            correlation_id=message.correlation_id,
            event_name=message.event,
            source=message.source,
        )
        return message


rmq_publisher = RMQPublisher(client=rmq_client)
