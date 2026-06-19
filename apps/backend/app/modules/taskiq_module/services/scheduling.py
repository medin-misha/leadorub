from datetime import datetime, timedelta, timezone

from taskiq import AsyncTaskiqTask
from taskiq.decor import AsyncTaskiqDecoratedTask
from taskiq.scheduler.scheduled_task import ScheduledTask
from taskiq_redis import RedisScheduleSource

from app.modules.taskiq_module.exceptions import TaskiqConfigurationError

from .datetime import ensure_utc
from .source import schedule_source


def _require_source() -> RedisScheduleSource:
    """Гарантирует, что schedule source настроен, иначе — понятная ошибка."""
    if schedule_source is None:
        raise TaskiqConfigurationError(
            "Scheduling is unavailable: taskiq is disabled or redis_url is not configured."
        )
    return schedule_source


async def schedule_task_at(
    task: AsyncTaskiqDecoratedTask,
    when: datetime,
    *args,
    **kwargs,
) -> str:
    """Отложить любую таску на конкретный момент (дата приводится к UTC)."""
    source = _require_source()
    created = await task.schedule_by_time(source, ensure_utc(when), *args, **kwargs)
    return created.schedule_id


async def schedule_task_after(
    task: AsyncTaskiqDecoratedTask,
    delay: timedelta,
    *args,
    **kwargs,
) -> str:
    """Отложить любую таску на интервал от текущего момента (в UTC)."""
    return await schedule_task_at(
        task, datetime.now(timezone.utc) + delay, *args, **kwargs
    )


async def schedule_task_cron(
    task: AsyncTaskiqDecoratedTask,
    cron: str,
    *args,
    **kwargs,
) -> str:
    """Запланировать повторяющийся запуск таски по cron-выражению (в UTC)."""
    source = _require_source()
    created = await task.schedule_by_cron(source, cron, *args, **kwargs)
    return created.schedule_id


async def cancel_scheduled_task(schedule_id: str) -> None:
    """Отменить ранее запланированную таску по её schedule_id."""
    source = _require_source()
    await source.delete_schedule(schedule_id)


async def list_scheduled_tasks() -> list[ScheduledTask]:
    """Вернуть все активные расписания из источника."""
    source = _require_source()
    return await source.get_schedules()


async def enqueue_task(
    task: AsyncTaskiqDecoratedTask,
    *args,
    **kwargs,
) -> AsyncTaskiqTask:
    """Немедленно поставить таску в очередь (без отложки).

    Возвращает AsyncTaskiqTask: при включённом result backend по нему можно
    дождаться результат через .wait_result().
    """
    return await task.kiq(*args, **kwargs)
