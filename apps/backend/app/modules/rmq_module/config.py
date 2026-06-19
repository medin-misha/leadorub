from pydantic import BaseModel, Field

from app.core.config import MainSettings, settings


class RMQModuleSettings(BaseModel):
    enabled: bool = True
    amqp_url: str | None = None
    default_exchange: str = "app.events"
    default_exchange_type: str = "direct"
    default_queue: str = "app.events.default"
    default_routing_key: str = "app.events.default"
    prefetch_count: int = Field(default=10, ge=1)
    consumer_enabled: bool = True
    publish_timeout: int = Field(default=5, ge=1)
    reconnect_interval: int = Field(default=5, ge=1)
    debug_endpoints_enabled: bool = False
    debug: bool = False

    @property
    def configured(self) -> bool:
        return self.enabled and bool(self.amqp_url)


def build_rmq_settings(main_settings: MainSettings = settings) -> RMQModuleSettings:
    return RMQModuleSettings(
        enabled=main_settings.rabbitmq_enabled,
        amqp_url=main_settings.amqp_url,
        default_exchange=main_settings.rabbitmq_default_exchange,
        default_exchange_type=main_settings.rabbitmq_default_exchange_type,
        default_queue=main_settings.rabbitmq_default_queue,
        default_routing_key=main_settings.rabbitmq_default_routing_key,
        prefetch_count=main_settings.rabbitmq_prefetch_count,
        consumer_enabled=main_settings.rabbitmq_consumer_enabled,
        publish_timeout=main_settings.rabbitmq_publish_timeout,
        reconnect_interval=main_settings.rabbitmq_reconnect_interval,
        debug_endpoints_enabled=main_settings.debug
        and main_settings.rabbitmq_debug_endpoints_enabled,
        debug=main_settings.debug,
    )


rmq_settings = build_rmq_settings()
