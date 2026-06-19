FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_PREFERENCE=only-system \
    UV_PYTHON=python3

WORKDIR /app

# Сначала кешируем зависимости
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Копируем проект и синхронизируем
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Финальный образ для рантайма
FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Создаем непривилегированного пользователя
RUN groupadd -g 10001 appuser && \
    useradd -u 10001 -g appuser -m -s /bin/bash appuser

COPY --from=builder --chown=appuser:appuser /app /app

# Гарантируем исполняемость entrypoint независимо от прав в build-контексте
RUN chmod +x /app/docker-entrypoint.sh

USER appuser

# Порт по умолчанию для API
EXPOSE 8000

# entrypoint ждёт готовности БД и накатывает миграции (alembic upgrade head),
# затем запускает CMD. exec "$@" в скрипте делает uvicorn PID 1 (корректные сигналы).
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
