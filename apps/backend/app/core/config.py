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
    redis_url: str | None = None
    taskiq_schedule_prefix: str = "schedule"
    taskiq_debug_endpoints_enabled: bool = False


settings = MainSettings()
