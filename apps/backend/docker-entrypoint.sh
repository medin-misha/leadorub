#!/bin/sh
# Точка входа backend-контейнера.
#
# Порядок:
#   1) ждём, пока PostgreSQL начнёт принимать соединения;
#   2) накатываем миграции Alembic до head (идемпотентно: если уже на head — no-op);
#   3) запускаем переданную команду (CMD), например uvicorn.
#
# set -e: если миграция упадёт, контейнер завершится с ошибкой, а не стартует
# приложение поверх неконсистентной схемы (безопасное поведение).
set -e

echo "[entrypoint] Ожидание готовности базы данных..."
python /app/scripts/wait_for_db.py

echo "[entrypoint] Применение миграций Alembic (upgrade head)..."
alembic upgrade head

echo "[entrypoint] Старт приложения: $*"
exec "$@"
