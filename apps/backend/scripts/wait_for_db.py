"""
Ожидание готовности PostgreSQL перед запуском миграций и приложения.

Запускается из ``docker-entrypoint.sh``. Строку подключения берёт из переменной
окружения ``database_url`` (тот же формат, что у SQLAlchemy:
``postgresql+asyncpg://...``) и пытается подключиться с ретраями.

Нужно потому, что backend живёт в ``docker-compose.apps.yml``, а PostgreSQL —
в ``docker-compose.infra.yml`` (разные compose-проекты), поэтому полноценный
``depends_on`` с healthcheck между ними недоступен: контейнер может стартовать
раньше, чем БД примет соединения.

Выходит с кодом 1, если БД не поднялась за отведённое время (RETRIES * DELAY).
"""

import asyncio
import os
import sys

import asyncpg

# Итоговое максимальное ожидание ≈ RETRIES * DELAY секунд.
RETRIES = 60
DELAY = 2.0


async def wait() -> None:
    raw_url = os.environ.get("database_url")
    if not raw_url:
        print(
            "wait_for_db: переменная окружения 'database_url' не задана",
            file=sys.stderr,
        )
        sys.exit(1)

    # asyncpg.connect не понимает SQLAlchemy-диалект '+asyncpg' в схеме URL.
    dsn = raw_url.replace("+asyncpg", "", 1)

    last_err: Exception | None = None
    for attempt in range(1, RETRIES + 1):
        try:
            conn = await asyncpg.connect(dsn)
            await conn.close()
            print(f"wait_for_db: БД готова (попытка {attempt})")
            return
        except Exception as err:  # OSError, asyncpg.*Error и пр.
            last_err = err
            print(f"wait_for_db: БД ещё не готова (попытка {attempt}/{RETRIES}): {err}")
            await asyncio.sleep(DELAY)

    print(
        f"wait_for_db: БД не поднялась за отведённое время: {last_err}",
        file=sys.stderr,
    )
    sys.exit(1)


if __name__ == "__main__":
    asyncio.run(wait())
