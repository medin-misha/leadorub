"""
Воронка DMCAGuardian для агентств: стартовая цепочка выдачи материалов.

Модуль не регистрирует собственный router: у него нет callback- или
message-хендлеров (обе inline-кнопки — URL и WebApp, они обрабатываются
клиентом Telegram). Вход в воронку — вызов `run_start_funnel` из
системного хендлера /start при deep-link payload `business`.
"""

import asyncio
import logging

from aiogram.types import FSInputFile, Message

from app.core import settings
from app.modules.business.keyboards import get_contact_keyboard
from app.modules.business.messages import get_messages

logger = logging.getLogger(__name__)

# Deep-link payload команды /start, ведущий в эту воронку (t.me/<bot>?start=business).
BUSINESS_START_PAYLOAD = "business"

# Именованное состояние воронки в backend (`user_stats.state`).
BUSINESS_START_STATE = "business_start"

GUIDE_FILENAME = "DMCAGuardian для агентств — защита моделей и контента.pdf"

# Паузы между сообщениями: welcome обещает файл «через пару секунд»,
# а видео должно прийти после файла — его подпись ссылается на «файл выше».
_GUIDE_DELAY_SECONDS = 2.0
_VIDEO_DELAY_SECONDS = 1.0

_MESSAGES = get_messages()


async def run_start_funnel(message: Message) -> None:
    """Проводит агентство по стартовой цепочке: текст → PDF → видео с кнопками."""

    await message.answer(_MESSAGES["welcome"])

    await asyncio.sleep(_GUIDE_DELAY_SECONDS)
    await _send_guide(message)

    await asyncio.sleep(_VIDEO_DELAY_SECONDS)
    await _send_video(message)

    await _mark_business_start(message)


async def _send_guide(message: Message) -> None:
    """Отправляет PDF-гайд; отсутствие файла логируется, но не роняет цепочку."""

    guide_path = settings.business_guide_path
    if not guide_path.is_file():
        logger.error("Business guide is missing: %s", guide_path)
        return

    await message.answer_document(
        document=FSInputFile(guide_path, filename=GUIDE_FILENAME),
        caption=_MESSAGES["guide_caption"],
    )


async def _send_video(message: Message) -> None:
    """Отправляет видео с кнопками связи; без файла кнопки уходят текстом."""

    video_path = settings.business_video_path
    keyboard = get_contact_keyboard()

    if not video_path.is_file():
        logger.error("Business video is missing: %s", video_path)
        await message.answer(_MESSAGES["video_caption"], reply_markup=keyboard)
        return

    await message.answer_video(
        video=FSInputFile(video_path),
        caption=_MESSAGES["video_caption"],
        reply_markup=keyboard,
    )


async def _mark_business_start(message: Message) -> None:
    """Фиксирует состояние воронки в backend, не роняя выдачу материалов.

    Состояние живёт в backend (`user_stats.state`): бот — тонкий транспорт
    без собственного хранилища. Сбой backend не должен ломать UX /start,
    поэтому ошибка только логируется.
    """

    # Ленивый импорт разрывает цикл: system.handlers импортирует эту воронку,
    # а system.client тянет за собой app.modules.system.__init__ -> handlers.
    from app.modules.system.client import BackendClientError, get_backend_client

    telegram_user = message.from_user
    if telegram_user is None:
        return

    try:
        client = get_backend_client()
        await client.set_user_state(
            telegram_id=telegram_user.id,
            state=BUSINESS_START_STATE,
        )
    except BackendClientError:
        logger.warning(
            "Failed to set state %s for user %s.",
            BUSINESS_START_STATE,
            telegram_user.id,
            exc_info=True,
        )
