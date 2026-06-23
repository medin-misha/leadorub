"""Резолвер вложений рассылки: id модели File бэкенда → байты файла.

Бот не имеет доступа к S3/БД бэкенда, поэтому скачивает файл по HTTP через
существующий backend API (`GET /api/files/{id}`), используя BACKEND_URL.
"""

import logging

import aiohttp

from app.core import settings

logger = logging.getLogger(__name__)


def build_file_url(file_id: int) -> str:
    """Строит URL скачивания файла из бэкенда по id модели File."""
    if not settings.backend_url:
        raise RuntimeError("BACKEND_URL is not configured; cannot resolve file_id")
    base = settings.backend_url.rstrip("/")
    prefix = settings.backend_api_prefix
    return f"{base}{prefix}/files/{file_id}"


async def fetch_file(file_id: int) -> tuple[bytes, str]:
    """Скачивает файл из бэкенда → (байты, content_type)."""
    url = build_file_url(file_id)
    timeout = aiohttp.ClientTimeout(total=settings.backend_request_timeout)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as response:
            response.raise_for_status()
            content_type = response.headers.get(
                "Content-Type", "application/octet-stream"
            )
            data = await response.read()
    logger.info("[notification] fetched file_id=%s (%s, %d bytes)", file_id, content_type, len(data))
    return data, content_type
