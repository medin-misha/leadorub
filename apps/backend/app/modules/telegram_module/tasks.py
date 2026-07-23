"""TaskIQ-таски telegram_module. Файл авто-обнаруживается discovery.py."""

from app.modules.taskiq_module.broker import broker

from .services.drip_sweep import run_drip_sweep


# Cron раз в минуту: гранулярность send_time правил — минуты. Статическое
# расписание в декораторе подхватывает LabelScheduleSource планировщика
# (taskiq_module/scheduler.py); без запущенных worker+scheduler не выполняется.
@broker.task(schedule=[{"cron": "* * * * *"}])
async def drip_newsletter_sweep() -> int:
    """Ставит «дозревшие» капельные рассылки в outbox. No-op при drip_enabled=false."""
    return await run_drip_sweep()
