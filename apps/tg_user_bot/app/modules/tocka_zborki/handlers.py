"""Telegram-хендлеры воронки фитнес-тренера."""

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, FSInputFile, Message

from app.core import settings

from app.modules.tocka_zborki.keyboards import (
    CALLBACK_GET_GUIDE,
    get_consultation_keyboard,
)
from app.modules.tocka_zborki.messages import get_messages

logger = logging.getLogger(__name__)
router = Router(name="tocka_zborki")
_MESSAGES = get_messages()


@router.callback_query(F.data == CALLBACK_GET_GUIDE)
async def send_training_guide(query: CallbackQuery) -> None:
    """Выдаёт PDF-пособие и открывает вход в Mini App."""
    if not query.message or not isinstance(query.message, Message):
        await query.answer()
        return

    guide_path = settings.training_guide_path
    if not guide_path.is_file():
        logger.error("Training guide is missing: %s", guide_path)
        await query.answer(_MESSAGES["guide_unavailable"], show_alert=True)
        return

    await query.answer()
    await query.message.answer_document(
        document=FSInputFile(guide_path, filename="Сила творожка.pdf")
    )
    await query.message.edit_text(
        text=_MESSAGES["guide_received"],
        reply_markup=get_consultation_keyboard(),
    )
