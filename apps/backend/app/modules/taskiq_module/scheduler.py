from taskiq import TaskiqScheduler
from taskiq.schedule_sources import LabelScheduleSource

from .broker import broker
from .config import taskiq_settings
from .discovery import discover_module_tasks
from .services.source import schedule_source

# Планировщик запускается отдельным процессом и обращается к таскам по их
# определениям, поэтому подгружаем все tasks.py ещё на импорте модуля.
discover_module_tasks()

scheduler: TaskiqScheduler | None = None

if taskiq_settings.enabled:
    # LabelScheduleSource читает статические cron-расписания, объявленные прямо
    # в декораторах @broker.task(schedule=[...]) (например, drip-sweep из
    # telegram_module). Без него такие таски никогда не запустятся: Redis-источник
    # хранит только динамические расписания, созданные через services/scheduling.
    sources: list = [LabelScheduleSource(broker)]
    if schedule_source is not None:
        sources.append(schedule_source)
    scheduler = TaskiqScheduler(broker=broker, sources=sources)
