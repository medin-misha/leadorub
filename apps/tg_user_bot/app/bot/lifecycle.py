"""
Lifecycle-хуки Telegram-приложения.

Файл отвечает за действия на startup/shutdown всего процесса: очистку webhook,
инициализацию системных runtime-ресурсов и корректное закрытие сетевых
подключений при остановке.
"""

import logging

from aiogram import Bot, Dispatcher

from app.core import MainSettings
from app.modules.rmq_module.runtime import shutdown_rmq_runtime, startup_rmq_runtime
from app.modules.system.runtime import shutdown_system_runtime, startup_system_runtime

logger = logging.getLogger(__name__)


def register_lifecycle(dispatcher: Dispatcher, settings: MainSettings) -> None:
    """Регистрирует startup/shutdown callbacks для всего runtime бота."""

    async def on_startup(bot: Bot) -> None:
        """Подготавливает Telegram и системный runtime к старту polling."""

        await bot.delete_webhook(drop_pending_updates=settings.drop_pending_updates)
        await startup_system_runtime(settings)
        await startup_rmq_runtime(settings)
        logger.info("Bot %s started in polling mode", settings.project_name)

    async def on_shutdown(bot: Bot) -> None:
        """Корректно закрывает runtime-ресурсы при остановке процесса."""

        logger.info("Bot %s is shutting down", settings.project_name)
        await shutdown_rmq_runtime()
        await shutdown_system_runtime()
        await bot.session.close()

    dispatcher.startup.register(on_startup)
    dispatcher.shutdown.register(on_shutdown)
