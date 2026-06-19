from taskiq_redis import RedisScheduleSource

from app.modules.taskiq_module.config import taskiq_settings

# Источник расписаний на Redis. Хранит отложенные таски (по времени и cron) и
# опрашивается отдельным процессом TaskiqScheduler. Создаётся только когда
# планирование действительно доступно (taskiq включён и задан redis_url),
# иначе остаётся None — хелперы планирования вернут понятную ошибку.
schedule_source: RedisScheduleSource | None = None

if taskiq_settings.scheduling_enabled:
    schedule_source = RedisScheduleSource(
        url=taskiq_settings.redis_url,
        prefix=taskiq_settings.schedule_prefix,
    )
