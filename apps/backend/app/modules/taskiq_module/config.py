from pydantic import BaseModel

from app.core.config import MainSettings, settings


class TaskiqModuleSettings(BaseModel):
    """Проекция настроек taskiq из глобального MainSettings.

    Подмодули читают конфигурацию отсюда, а не из .env напрямую — так модуль
    остаётся переносимым и тестируемым (можно собрать настройки руками).
    """

    enabled: bool = False
    amqp_url: str | None = None
    redis_url: str | None = None
    schedule_prefix: str = "schedule"
    debug: bool = False
    debug_endpoints_enabled: bool = False

    @property
    def configured(self) -> bool:
        """taskiq полностью готов: включён и есть оба транспорта (RabbitMQ + Redis)."""
        return self.enabled and bool(self.amqp_url) and bool(self.redis_url)

    @property
    def scheduling_enabled(self) -> bool:
        """Планирование доступно: нужен Redis как schedule source."""
        return self.enabled and bool(self.redis_url)


def build_taskiq_settings(
    main_settings: MainSettings = settings,
) -> TaskiqModuleSettings:
    return TaskiqModuleSettings(
        enabled=main_settings.taskiq_enabled,
        amqp_url=main_settings.amqp_url,
        redis_url=main_settings.redis_url,
        schedule_prefix=main_settings.taskiq_schedule_prefix,
        debug=main_settings.debug,
        debug_endpoints_enabled=main_settings.taskiq_debug_endpoints_enabled,
    )


taskiq_settings = build_taskiq_settings()
