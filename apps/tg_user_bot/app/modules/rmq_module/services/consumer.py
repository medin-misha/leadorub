import asyncio
from logging import getLogger

from aio_pika.abc import AbstractIncomingMessage
from pydantic import ValidationError

from app.modules.rmq_module.config import rmq_settings
from app.modules.rmq_module.schemas import RMQMessage

from .client import RMQClient
from .registry import ConsumerRegistration
from .topology import ExchangeSpec, QueueSpec

logger = getLogger(__name__)


class RetryableRMQError(RuntimeError):
    """Ошибка handler-а, после которой сообщение нужно вернуть в очередь."""


class RMQConsumerService:
    def __init__(self, client: RMQClient) -> None:
        self._client = client

    async def run_registration(
        self,
        registration: ConsumerRegistration,
        *,
        stop_event: asyncio.Event,
    ) -> None:
        while not stop_event.is_set():
            try:
                if registration.auto_declare:
                    await self._client.ensure_topology(
                        exchange=ExchangeSpec(
                            name=registration.exchange_name,
                            exchange_type=registration.exchange_type,
                        ),
                        queue=QueueSpec(
                            name=registration.queue_name,
                            routing_key=registration.routing_key,
                        ),
                    )
                await self._client.consume(
                    queue_name=registration.queue_name,
                    callback=lambda incoming: self._handle_message(
                        incoming, registration
                    ),
                )
                await stop_event.wait()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception(
                    "RMQ consumer loop failed for queue '%s'",
                    registration.queue_name,
                )
                await asyncio.sleep(rmq_settings.rabbitmq_reconnect_interval)

    async def _handle_message(
        self,
        incoming: AbstractIncomingMessage,
        registration: ConsumerRegistration,
    ) -> None:
        try:
            message = RMQMessage.model_validate_json(incoming.body)
        except ValidationError:
            logger.exception(
                "RMQ message validation failed for queue '%s'",
                registration.queue_name,
            )
            await incoming.reject(requeue=False)
            return

        try:
            await registration.handler(message)
        except RetryableRMQError:
            logger.warning(
                "RMQ consumer handler requested retry for queue '%s'",
                registration.queue_name,
                exc_info=True,
            )
            await incoming.reject(requeue=True)
            return
        except Exception:
            logger.exception(
                "RMQ consumer handler failed for queue '%s'",
                registration.queue_name,
            )
            await incoming.reject(requeue=False)
            return

        await incoming.ack()
