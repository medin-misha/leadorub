from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from app.modules.rmq_module.schemas import RMQMessage

RMQConsumerHandler = Callable[[RMQMessage], Awaitable[None]]


@dataclass(slots=True, frozen=True)
class ConsumerRegistration:
    queue_name: str
    exchange_name: str
    routing_key: str
    handler: RMQConsumerHandler
    exchange_type: str = "direct"
    auto_declare: bool = True

    @property
    def handler_name(self) -> str:
        return getattr(self.handler, "__name__", self.handler.__class__.__name__)


class RMQConsumerRegistry:
    def __init__(self) -> None:
        self._registrations: list[ConsumerRegistration] = []

    def register(
        self,
        *,
        queue_name: str,
        exchange_name: str,
        routing_key: str,
        handler: RMQConsumerHandler,
        exchange_type: str = "direct",
        auto_declare: bool = True,
    ) -> ConsumerRegistration:
        registration = ConsumerRegistration(
            queue_name=queue_name,
            exchange_name=exchange_name,
            routing_key=routing_key,
            handler=handler,
            exchange_type=exchange_type,
            auto_declare=auto_declare,
        )
        if registration in self._registrations:
            return registration

        for existing in self._registrations:
            if (
                existing.queue_name == queue_name
                and existing.exchange_name == exchange_name
                and existing.routing_key == routing_key
            ):
                raise ValueError(
                    "Consumer registration already exists for this queue, exchange, and routing key"
                )
        self._registrations.append(registration)
        return registration

    def registrations(self) -> list[ConsumerRegistration]:
        return list(self._registrations)

    def describe(self) -> list[dict[str, str | bool]]:
        return [
            {
                "queue_name": registration.queue_name,
                "exchange_name": registration.exchange_name,
                "routing_key": registration.routing_key,
                "exchange_type": registration.exchange_type,
                "handler_name": registration.handler_name,
                "auto_declare": registration.auto_declare,
            }
            for registration in self._registrations
        ]


rmq_registry = RMQConsumerRegistry()


def register_consumer(
    *,
    queue_name: str,
    exchange_name: str,
    routing_key: str,
    handler: RMQConsumerHandler,
    exchange_type: str = "direct",
    auto_declare: bool = True,
) -> ConsumerRegistration:
    return rmq_registry.register(
        queue_name=queue_name,
        exchange_name=exchange_name,
        routing_key=routing_key,
        handler=handler,
        exchange_type=exchange_type,
        auto_declare=auto_declare,
    )
