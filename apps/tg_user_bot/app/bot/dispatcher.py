"""
Создание и первичная настройка `aiogram.Dispatcher`.

Файл нужен как точка расширения для будущих middleware, filters и общих
настроек роутинга, не перегружая точку входа и сборку приложения.
"""

from aiogram import Dispatcher

from app.bot.registry import register_routers


def create_dispatcher() -> Dispatcher:
    """Создает dispatcher и подключает к нему модульные роутеры."""

    dispatcher = Dispatcher()
    register_routers(dispatcher)
    return dispatcher
