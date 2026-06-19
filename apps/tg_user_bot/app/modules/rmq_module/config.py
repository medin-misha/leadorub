"""
Конфигурация RabbitMQ-модуля Telegram-шаблона.

Модуль проецирует RMQ-настройки из общего `app.core.settings`, чтобы
RabbitMQ-параметры жили в одном конфигурационном слое вместе с остальными
process-level настройками бота.
"""

from dataclasses import dataclass

from app.core.config import MainSettings, settings


class RMQConfigurationError(RuntimeError):
    """Raised when RabbitMQ is used without the required configuration."""


@dataclass(slots=True)
class RMQSettings:
    """Настройки транспортного RabbitMQ-модуля."""

    amqp_url: str | None
    rabbitmq_default_exchange: str
    rabbitmq_default_exchange_type: str
    rabbitmq_default_queue: str
    rabbitmq_default_routing_key: str
    rabbitmq_prefetch_count: int
    rabbitmq_consumer_enabled: bool
    rabbitmq_publish_timeout: int
    rabbitmq_reconnect_interval: int

    @classmethod
    def from_app_settings(cls, app_settings: MainSettings) -> "RMQSettings":
        return cls(
            amqp_url=app_settings.amqp_url,
            rabbitmq_default_exchange=app_settings.rabbitmq_default_exchange,
            rabbitmq_default_exchange_type=app_settings.rabbitmq_default_exchange_type,
            rabbitmq_default_queue=app_settings.rabbitmq_default_queue,
            rabbitmq_default_routing_key=app_settings.rabbitmq_default_routing_key,
            rabbitmq_prefetch_count=app_settings.rabbitmq_prefetch_count,
            rabbitmq_consumer_enabled=app_settings.rabbitmq_consumer_enabled,
            rabbitmq_publish_timeout=app_settings.rabbitmq_publish_timeout,
            rabbitmq_reconnect_interval=app_settings.rabbitmq_reconnect_interval,
        )

    def require_amqp_url(self) -> str:
        if self.amqp_url:
            return self.amqp_url
        raise RMQConfigurationError(
            "AMQP_URL is required when RabbitMQ publisher or consumer runtime is used"
        )


rmq_settings = RMQSettings.from_app_settings(settings)
