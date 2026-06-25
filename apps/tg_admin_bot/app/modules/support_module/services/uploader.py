"""Загрузка входящего медиа поддержки на backend.

Бинарь не гоняем через RMQ: бот скачивает файл из Telegram и POST-ит его на
`POST /api/chat/inbound-media` (server-to-server, X-Service-Token). Backend
заливает файл в S3 и создаёт строку chat_message(direction='user', file_id).
"""

import logging

import aiohttp

from app.core import settings

logger = logging.getLogger(__name__)

# Заливка тяжелее обычного JSON-запроса — даём отдельный, больший таймаут.
_UPLOAD_TIMEOUT_SECONDS = 60


def _media_url() -> str:
    if not settings.backend_url:
        raise RuntimeError("BACKEND_URL is not configured; cannot upload media")
    base = settings.backend_url.rstrip("/")
    prefix = settings.backend_api_prefix
    return f"{base}{prefix}/chat/inbound-media"


async def upload_inbound_media(
    *,
    telegram_id: int,
    data: bytes,
    filename: str,
    content_type: str,
    caption: str | None = None,
    tg_message_id: int | None = None,
) -> None:
    """Шлёт скачанный файл на backend multipart'ом. Бросает при не-2xx ответе."""
    url = _media_url()
    timeout = aiohttp.ClientTimeout(total=_UPLOAD_TIMEOUT_SECONDS)
    headers: dict[str, str] = {}
    if settings.backend_service_token:
        headers["X-Service-Token"] = settings.backend_service_token

    form = aiohttp.FormData()
    form.add_field("telegram_id", str(telegram_id))
    if tg_message_id is not None:
        form.add_field("tg_message_id", str(tg_message_id))
    if caption:
        form.add_field("caption", caption)
    form.add_field("file", data, filename=filename, content_type=content_type)

    async with aiohttp.ClientSession(
        timeout=timeout, headers=headers or None
    ) as session:
        async with session.post(url, data=form) as response:
            response.raise_for_status()

    logger.info(
        "[support] uploaded media telegram_id=%s (%s, %d bytes)",
        telegram_id,
        content_type,
        len(data),
    )
