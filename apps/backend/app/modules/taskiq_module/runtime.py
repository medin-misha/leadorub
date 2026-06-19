from logging import getLogger

from .broker import broker
from .config import taskiq_settings
from .discovery import discover_module_tasks
from .exceptions import TaskiqConfigurationError
from .services.source import schedule_source

logger = getLogger(__name__)


async def startup_taskiq_runtime() -> None:
    """Старт taskiq в API-процессе (вызывается из app/lifecycle.py).

    Воркер и планировщик — отдельные процессы со своим жизненным циклом, поэтому
    здесь работаем только в обычном (не worker) процессе: поднимаем подключения
    broker и schedule source и подгружаем таски, чтобы их можно было планировать.
    """
    if not taskiq_settings.enabled:
        logger.info("taskiq module is disabled; skipping startup")
        return

    if broker.is_worker_process:
        return

    if not taskiq_settings.amqp_url:
        raise TaskiqConfigurationError(
            "taskiq is enabled, but amqp_url is not configured."
        )
    if not taskiq_settings.redis_url:
        raise TaskiqConfigurationError(
            "taskiq is enabled, but redis_url is not configured."
        )

    discover_module_tasks()
    await broker.startup()
    if schedule_source is not None:
        await schedule_source.startup()


async def shutdown_taskiq_runtime() -> None:
    if not taskiq_settings.enabled or broker.is_worker_process:
        return

    if schedule_source is not None:
        await schedule_source.shutdown()
    await broker.shutdown()
