"""Базовая настройка process-wide logging для Telegram-приложения."""

import logging


def setup_logging(debug: bool) -> None:
    """Настраивает базовое логирование для всего процесса."""

    logging.basicConfig(
        level=logging.INFO if debug else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        force=True,
    )
