import asyncio
import logging

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.types import (
    BufferedInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)

from app.core import settings
from ..schemas import TelegramNotification
from .backend_files import fetch_file

logger = logging.getLogger(__name__)

# Отдельный Bot-инстанс только для фоновых рассылок.
bot = Bot(
    token=settings.bot_token,
    default=DefaultBotProperties(parse_mode=settings.bot_parse_mode),
)

# Лёгкий троттлинг между отправками (Telegram ~30 msg/s на разные чаты).
THROTTLE_SECONDS = 0.05


def build_markup(use_buttons, buttons):
    """Собирает клавиатуру из плоского списка кнопок: каждая кнопка — отдельный ряд."""
    if not use_buttons or not buttons:
        return None

    if use_buttons == "INLINE":
        rows = []
        for btn in buttons:
            kwargs = {"text": btn.text}
            if btn.url:
                kwargs["url"] = btn.url
            elif btn.callback_data:
                kwargs["callback_data"] = btn.callback_data
            elif btn.web_app:
                kwargs["web_app"] = WebAppInfo(url=btn.web_app)
            else:
                # последний фолбэк: inline-кнопке нужен хоть один target
                kwargs["callback_data"] = btn.text
            rows.append([InlineKeyboardButton(**kwargs)])
        return InlineKeyboardMarkup(inline_keyboard=rows)

    if use_buttons == "REPLY":
        rows = []
        for btn in buttons:
            kwargs = {"text": btn.text}
            if btn.requests_contect:
                kwargs["request_contact"] = True
            if btn.request_location:
                kwargs["request_location"] = True
            if btn.web_app:
                kwargs["web_app"] = WebAppInfo(url=btn.web_app)
            rows.append([KeyboardButton(**kwargs)])
        return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)

    return None


def is_photo(content_type: str) -> bool:
    """Картинки шлём через send_photo, остальное — send_document."""
    return content_type.startswith("image/")


async def send_notification(notification: TelegramNotification) -> None:
    """Рассылает одно уведомление по всему списку chat_ids.

    Если есть file_id — файл скачивается из бэкенда один раз; первому получателю
    шлём байтами, дальше переиспользуем Telegram file_id из ответа.
    """
    reply_markup = build_markup(notification.use_buttons, notification.buttons)

    if notification.file_id is not None:
        await _broadcast_file(notification, reply_markup)
    else:
        await _broadcast_text(notification, reply_markup)


async def _broadcast_text(notification: TelegramNotification, reply_markup) -> None:
    for chat_id in notification.chat_ids:
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=notification.message or "",
                reply_markup=reply_markup,
            )
        except Exception:
            logger.exception(
                "[notification] send_message failed for chat_id=%s", chat_id
            )
        await asyncio.sleep(THROTTLE_SECONDS)


async def _broadcast_file(notification: TelegramNotification, reply_markup) -> None:
    data, content_type = await fetch_file(notification.file_id)
    photo = is_photo(content_type)
    tg_file_id: str | None = None  # пойманный Telegram file_id для переиспользования

    for chat_id in notification.chat_ids:
        # первый раз — байты; дальше — уже загруженный Telegram file_id
        media = tg_file_id or BufferedInputFile(
            data, filename=f"file_{notification.file_id}"
        )
        try:
            if photo:
                message = await bot.send_photo(
                    chat_id=chat_id,
                    photo=media,
                    caption=notification.message,
                    reply_markup=reply_markup,
                )
                if tg_file_id is None and message.photo:
                    tg_file_id = message.photo[-1].file_id
            else:
                message = await bot.send_document(
                    chat_id=chat_id,
                    document=media,
                    caption=notification.message,
                    reply_markup=reply_markup,
                )
                if tg_file_id is None and message.document:
                    tg_file_id = message.document.file_id
        except Exception:
            logger.exception(
                "[notification] send file failed for chat_id=%s", chat_id
            )
        await asyncio.sleep(THROTTLE_SECONDS)
