"""
Lifecycle системного Telegram-модуля.

Здесь централизован startup/shutdown process-level ресурсов, которыми
пользуются все остальные Telegram-модули: backend HTTP-клиент и auth cache.
"""

from __future__ import annotations

from app.core import MainSettings

from .auth.cache import auth_cache
from .client import shutdown_backend_client, startup_backend_client


async def startup_system_runtime(_: MainSettings) -> None:
    """Поднимает runtime-ресурсы системного модуля перед началом polling."""

    auth_cache.clear()
    await startup_backend_client()


async def shutdown_system_runtime() -> None:
    """Корректно освобождает runtime-ресурсы системного модуля."""

    auth_cache.clear()
    await shutdown_backend_client()
