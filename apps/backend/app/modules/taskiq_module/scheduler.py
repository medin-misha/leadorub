from taskiq import TaskiqScheduler

from .broker import broker
from .discovery import discover_module_tasks
from .services.source import schedule_source

# Планировщик запускается отдельным процессом и обращается к таскам по их
# определениям, поэтому подгружаем все tasks.py ещё на импорте модуля.
discover_module_tasks()

scheduler: TaskiqScheduler | None = None

if schedule_source is not None:
    scheduler = TaskiqScheduler(broker=broker, sources=[schedule_source])
