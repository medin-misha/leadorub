"""
Сборка runtime-объектов Telegram-приложения.

Этот файл инкапсулирует создание `Bot`, `Dispatcher` и lifecycle-хуков, чтобы
точка входа оставалась тонкой и не знала детали внутренней архитектуры.
"""

from dataclasses import dataclass

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from app.bot.dispatcher import create_dispatcher
from app.bot.lifecycle import register_lifecycle
from app.core import MainSettings, settings


@dataclass(slots=True)
class TelegramApplication:
    """Контейнер с runtime-объектами собранного Telegram-приложения."""

    bot: Bot
    dispatcher: Dispatcher


def create_bot(app_settings: MainSettings) -> Bot:
    """Создает `aiogram.Bot` на основе общих настроек приложения."""

    default = DefaultBotProperties(parse_mode=app_settings.bot_parse_mode)
    return Bot(token=app_settings.bot_token, default=default)


def create_application(app_settings: MainSettings = settings) -> TelegramApplication:
    """Собирает Telegram-приложение из bot, dispatcher и lifecycle-хуков."""

    bot = create_bot(app_settings)
    dispatcher = create_dispatcher()
    register_lifecycle(dispatcher, app_settings)
    return TelegramApplication(bot=bot, dispatcher=dispatcher)


async def run_polling(app_settings: MainSettings = settings) -> None:
    """Запускает собранное приложение в polling-only режиме."""

    application = create_application(app_settings)
    await application.dispatcher.start_polling(application.bot)
