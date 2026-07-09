from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class MainSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Project
    project_name: str = "Fast API Template"
    debug: bool

    # CORS
    cors_origins: Any = ["*"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, str) and v.startswith("[") and v.endswith("]"):
            import json

            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return [str(i).strip() for i in parsed]
            except Exception:
                pass
        elif isinstance(v, list):
            return v
        return v

    # Services
    database_url: str
    database_pool_size: int = Field(default=5, ge=1)
    database_max_overflow: int = Field(default=10, ge=0)
    database_pool_timeout: int = Field(default=30, ge=1)
    database_pool_recycle: int = Field(default=1800, ge=0)

    # RabbitMQ
    rabbitmq_enabled: bool = True
    amqp_url: str | None = None
    rabbitmq_default_exchange: str = "app.events"
    rabbitmq_default_exchange_type: str = "direct"
    rabbitmq_default_queue: str = "app.events.default"
    rabbitmq_default_routing_key: str = "app.events.default"
    rabbitmq_prefetch_count: int = Field(default=10, ge=1)
    rabbitmq_consumer_enabled: bool = True
    rabbitmq_publish_timeout: int = Field(default=5, ge=1)
    rabbitmq_reconnect_interval: int = Field(default=5, ge=1)
    rabbitmq_debug_endpoints_enabled: bool = False

    # Storage
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str
    minio_secure: bool = False

    # taskiq
    taskiq_enabled: bool = False
    # Redis (taskiq result backend + schedule source).
    # Единый источник пароля — redis_password; redis_url собирается ниже (@property).
    # Хост/порт/db по умолчанию рассчитаны на docker-сеть (имя сервиса `redis`).
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str | None = None
    taskiq_schedule_prefix: str = "schedule"
    taskiq_debug_endpoints_enabled: bool = False

    # Newsletter
    # Размер чанка рассылки: бэкенд режет аудиторию на пачки по N получателей
    # и публикует одно RMQ-сообщение на пачку (см. план chunking+idempotency).
    newsletter_chunk_size: int = Field(default=500, ge=1)

    # Auth / Security
    # Bootstrap-админ создаётся при старте, если такого ещё нет (см. lifecycle).
    admin_username: str | None = None
    admin_password: str | None = None
    # Секрет для подписи JWT. Обязателен; генерируется случайно и хранится в .env.
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    # TTL access-токена в минутах (по умолчанию 12 часов).
    jwt_access_token_expire_minutes: int = Field(default=720, ge=1)
    # Общий статический токен для server-to-server вызовов (юзер-бот → backend).
    # Если None — сервисные эндпоинты отклоняют любые запросы по X-Service-Token.
    service_token: str | None = None
    # Токен бота для валидации Telegram initData
    user_bot: str | None = None

    @property
    def redis_url(self) -> str | None:
        """Строка подключения к Redis, собранная из единого redis_password.

        Возвращает None, если пароль не задан, — taskiq трактует это как
        «Redis не настроен» (сохраняем прежний контракт bool(redis_url))."""
        if not self.redis_password:
            return None
        return (
            f"redis://:{self.redis_password}@"
            f"{self.redis_host}:{self.redis_port}/{self.redis_db}"
        )


settings = MainSettings()
