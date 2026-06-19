"""
Модульная конфигурация системного слоя Telegram-шаблона.

Файл не читает `.env` напрямую. Вместо этого он строит проекцию поверх общего
`app.core.settings`, чтобы системный модуль имел собственный явный контракт
настроек, но не ломал идею единой центральной конфигурации приложения.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.core import MainSettings, settings


class SystemModuleSettings(BaseModel):
    """Явный набор настроек, которые нужны именно system-модулю."""

    backend_url: str | None = None
    backend_api_prefix: str = "/api"
    backend_request_timeout: float = Field(default=10.0, gt=0)
    auth_cache_max_size: int = Field(default=1000, ge=1)
    debug_commands_enabled: bool = False

    @property
    def backend_api_base_url(self) -> str | None:
        """Собирает базовый URL для HTTP API backend с учётом `/api`-префикса."""

        if not self.backend_url:
            return None

        normalized_url = self.backend_url.rstrip("/")
        normalized_prefix = self.backend_api_prefix.strip() or "/api"
        normalized_prefix = (
            normalized_prefix
            if normalized_prefix.startswith("/")
            else f"/{normalized_prefix}"
        )
        normalized_prefix = normalized_prefix.rstrip("/")

        if normalized_url.endswith(normalized_prefix):
            return normalized_url

        return f"{normalized_url}{normalized_prefix}"


def build_system_settings(
    main_settings: MainSettings = settings,
) -> SystemModuleSettings:
    """Строит системный конфиг из общего конфига Telegram-приложения."""

    return SystemModuleSettings(
        backend_url=main_settings.backend_url,
        backend_api_prefix=main_settings.backend_api_prefix,
        backend_request_timeout=main_settings.backend_request_timeout,
        auth_cache_max_size=main_settings.auth_cache_max_size,
        debug_commands_enabled=main_settings.debug,
    )


system_settings = build_system_settings()
