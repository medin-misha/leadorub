from logging import getLogger

from .config import rmq_settings
from .exceptions import RMQConfigurationError
from .services import build_outbox_runtime, rmq_registry, rmq_runtime

logger = getLogger(__name__)
outbox_runtime = build_outbox_runtime()


async def startup_rmq_runtime() -> None:
    if not rmq_settings.enabled:
        logger.info("RMQ module is disabled; skipping startup")
        return

    if not rmq_settings.amqp_url:
        raise RMQConfigurationError("RabbitMQ is enabled, but amqp_url is not configured.")

    await outbox_runtime.start()

    registrations = rmq_registry.registrations()
    if not registrations:
        logger.info("RMQ consumer runtime skipped: no registrations found")
        return

    if not rmq_settings.consumer_enabled:
        logger.info("RMQ runtime skipped: consumers are disabled in configuration")
        return

    if not rmq_settings.amqp_url:
        raise RMQConfigurationError(
            "RabbitMQ consumers are registered, but amqp_url is not configured."
        )

    await rmq_runtime.start()


async def shutdown_rmq_runtime() -> None:
    await outbox_runtime.stop()
    if rmq_runtime.started:
        await rmq_runtime.stop()
