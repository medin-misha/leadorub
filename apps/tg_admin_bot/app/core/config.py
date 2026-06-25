"""
Центральная конфигурация Telegram-приложения.

Этот файл является единственной точкой чтения общего `.env` и хранит как
настройки самого бота, так и общие параметры интеграции с backend, которые
дальше проецируются в модульные конфиги.
"""

from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class MainSettings(BaseSettings):
    """Общие настройки процесса Telegram-бота."""

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    project_name: str = "Telegram Template"
    drop_pending_updates: bool = True
    debug: bool = Field(default=False, validation_alias=AliasChoices("DEBUG", "debug"))
    token: SecretStr = Field(validation_alias="TOKEN")
    backend_url: str | None = Field(default=None, validation_alias="BACKEND_URL")
    backend_api_prefix: str = Field(
        default="/api", validation_alias="BACKEND_API_PREFIX"
    )
    backend_request_timeout: float = Field(
        default=10.0,
        validation_alias="BACKEND_REQUEST_TIMEOUT",
    )
    # Сервисный токен для server-to-server вызовов backend (X-Service-Token).
    # Общий секрет с backend: в infra/.env это `service_token`.
    backend_service_token: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SERVICE_TOKEN", "service_token"),
    )
    auth_cache_max_size: int = Field(
        default=1000, validation_alias="AUTH_CACHE_MAX_SIZE"
    )
    bot_parse_mode: str = Field(default="HTML", validation_alias="BOT_PARSE_MODE")
    amqp_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("AMQP_URL", "amqp_url"),
    )
    rabbitmq_default_exchange: str = Field(
        default="app.events",
        validation_alias=AliasChoices(
            "RABBITMQ_DEFAULT_EXCHANGE",
            "rabbitmq_default_exchange",
        ),
    )
    rabbitmq_default_exchange_type: str = Field(
        default="direct",
        validation_alias=AliasChoices(
            "RABBITMQ_DEFAULT_EXCHANGE_TYPE",
            "rabbitmq_default_exchange_type",
        ),
    )
    rabbitmq_default_queue: str = Field(
        default="app.events.default",
        validation_alias=AliasChoices(
            "RABBITMQ_DEFAULT_QUEUE",
            "rabbitmq_default_queue",
        ),
    )
    rabbitmq_default_routing_key: str = Field(
        default="app.events.default",
        validation_alias=AliasChoices(
            "RABBITMQ_DEFAULT_ROUTING_KEY",
            "rabbitmq_default_routing_key",
        ),
    )
    rabbitmq_prefetch_count: int = Field(
        default=10,
        ge=1,
        validation_alias=AliasChoices(
            "RABBITMQ_PREFETCH_COUNT",
            "rabbitmq_prefetch_count",
        ),
    )
    rabbitmq_consumer_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "RABBITMQ_CONSUMER_ENABLED",
            "rabbitmq_consumer_enabled",
        ),
    )
    rabbitmq_publish_timeout: int = Field(
        default=5,
        ge=1,
        validation_alias=AliasChoices(
            "RABBITMQ_PUBLISH_TIMEOUT",
            "rabbitmq_publish_timeout",
        ),
    )
    rabbitmq_reconnect_interval: int = Field(
        default=5,
        ge=1,
        validation_alias=AliasChoices(
            "RABBITMQ_RECONNECT_INTERVAL",
            "rabbitmq_reconnect_interval",
        ),
    )

    @property
    def bot_token(self) -> str:
        """Возвращает сырой токен в формате, который нужен aiogram."""

        return self.token.get_secret_value()


settings = MainSettings()
