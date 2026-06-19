"""
Точка входа в Telegram-приложение.

Файл специально оставлен тонким: он только включает логирование процесса и
передаёт управление слою сборки приложения, который уже знает, как поднять bot
runtime и polling.
"""

import asyncio

from app.bot import run_polling
from app.core import settings
from app.core.logging import setup_logging


async def main() -> None:
    """Настраивает процесс и запускает polling."""

    setup_logging(settings.debug)
    await run_polling(settings)


if __name__ == "__main__":
    asyncio.run(main())
