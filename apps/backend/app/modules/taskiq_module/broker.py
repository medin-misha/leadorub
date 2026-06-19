from taskiq import TaskiqEvents, TaskiqState
from taskiq_aio_pika import AioPikaBroker
from taskiq_redis import RedisAsyncResultBackend

from .config import taskiq_settings
from .discovery import discover_module_tasks

# RabbitMQ — транспорт исполнения тасок.
broker = AioPikaBroker(url=taskiq_settings.amqp_url)

# Redis-backend хранит результаты выполнения: при наличии redis_url .kiq() даёт
# AsyncTaskiqTask, по которому можно дождаться результат через .wait_result().
if taskiq_settings.redis_url:
    broker.with_result_backend(
        RedisAsyncResultBackend(redis_url=taskiq_settings.redis_url)
    )


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def _load_module_tasks(_: TaskiqState) -> None:
    # В worker-процессе таски нужно подгрузить перед началом потребления очереди,
    # иначе broker не найдёт обработчик по имени таски.
    discover_module_tasks()
