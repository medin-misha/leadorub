import asyncio
import html
import logging
from dataclasses import dataclass
from enum import Enum

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from aiogram.types import (
    BufferedInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)

from app.core import settings
from app.modules.rmq_module import RetryableRMQError
from ..schemas import TelegramNotification
from .backend_files import fetch_file
from .idempotency import idempotency_store

logger = logging.getLogger(__name__)

# Отдельный Bot-инстанс только для фоновых рассылок.
bot = Bot(
    token=settings.bot_token,
    default=DefaultBotProperties(parse_mode=settings.bot_parse_mode),
)

# Лёгкий троттлинг между отправками (Telegram ~30 msg/s на разные чаты).
THROTTLE_SECONDS = 0.05

# Сколько раз повторяем одну отправку при FloodWait (429), прежде чем сдаться.
# Защита от бесконечного цикла, если Telegram продолжает возвращать retry_after.
MAX_FLOOD_RETRIES = 5


class DeliveryStatus(Enum):
    DELIVERED = "delivered"
    PERMANENT_FAILURE = "permanent_failure"
    RETRYABLE_FAILURE = "retryable_failure"


@dataclass(frozen=True, slots=True)
class DeliveryResult:
    status: DeliveryStatus
    message: object | None = None


class NotificationDeliveryError(RetryableRMQError):
    """Хотя бы один адресат временно не получил уведомление."""


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


def escape_html(text: str | None) -> str | None:
    """Экранирует <, >, & для parse_mode=HTML.

    Бот отправляет с parse_mode=HTML, поэтому «сырые» <, >, & в тексте админа
    Telegram трактует как разметку и при поломке молча отклоняет сообщение
    (ошибка гасится в except ниже → получатель ничего не получает). Текст
    считаем простым и экранируем спецсимволы. quote=False — кавычки не трогаем
    (в теле HTML они валидны и так). None пробрасываем: подпись к файлу может
    отсутствовать.
    """
    if text is None:
        return None
    return html.escape(text, quote=False)


async def _send_with_retry(make_request, chat_id: int):
    """Отправляет одно сообщение с обработкой FloodWait (429) и блокировок (403).

    `make_request` — фабрика корутины отправки (например, `lambda: bot.send_message(...)`).
    Она вызывается заново на каждую попытку, потому что уже awaited-корутину
    переиспользовать нельзя.

    Поведение по типам ошибок:
    - `TelegramRetryAfter` (429, флуд-контроль): ждём РОВНО `retry_after` секунд и
      повторяем. Игнорировать нельзя — иначе продолжим долбить API и поймаем
      временный бан всего бота, а не одного получателя.
    - `TelegramForbiddenError` (403, бота заблокировали/чат удалён): ожидаемая
      ситуация, без стектрейса и без ретраев — этому получателю уже не доставить.
    - прочее: считаем временной ошибкой; после прохода по чанку RMQ повторит его,
      а уже успешные адресаты будут пропущены по Redis-маркеру.

    Возвращает явный статус доставки и `Message` при успехе.
    """
    for attempt in range(1, MAX_FLOOD_RETRIES + 1):
        try:
            return DeliveryResult(DeliveryStatus.DELIVERED, await make_request())
        except TelegramRetryAfter as exc:
            logger.warning(
                "[notification] flood limit on chat_id=%s: retry after %ss "
                "(attempt %s/%s)",
                chat_id,
                exc.retry_after,
                attempt,
                MAX_FLOOD_RETRIES,
            )
            await asyncio.sleep(exc.retry_after)
        except TelegramForbiddenError:
            logger.info("[notification] chat_id=%s blocked the bot, skipping", chat_id)
            return DeliveryResult(DeliveryStatus.PERMANENT_FAILURE)
        except Exception:
            logger.exception("[notification] send failed for chat_id=%s", chat_id)
            return DeliveryResult(DeliveryStatus.RETRYABLE_FAILURE)

    logger.error(
        "[notification] giving up on chat_id=%s after %s flood retries",
        chat_id,
        MAX_FLOOD_RETRIES,
    )
    return DeliveryResult(DeliveryStatus.RETRYABLE_FAILURE)


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
    retryable_chat_ids = []
    for chat_id in notification.chat_ids:
        # Дедуп: уже отправляли этому получателю в рамках этой рассылки — пропускаем.
        claim = await idempotency_store.claim(notification.broadcast_id, chat_id)
        if claim is None:
            continue
        result = await _send_with_retry(
            lambda chat_id=chat_id: bot.send_message(
                chat_id=chat_id,
                text=escape_html(notification.message or ""),
                reply_markup=reply_markup,
            ),
            chat_id,
        )
        if result.status is DeliveryStatus.RETRYABLE_FAILURE:
            await idempotency_store.release(claim)
            retryable_chat_ids.append(chat_id)
        else:
            await idempotency_store.complete(claim)
        await asyncio.sleep(THROTTLE_SECONDS)

    if retryable_chat_ids:
        raise NotificationDeliveryError(
            f"temporary Telegram delivery failure for chat_ids={retryable_chat_ids}"
        )


async def _broadcast_file(notification: TelegramNotification, reply_markup) -> None:
    data, content_type = await fetch_file(notification.file_id)
    photo = is_photo(content_type)
    tg_file_id: str | None = None  # пойманный Telegram file_id для переиспользования
    retryable_chat_ids = []

    for chat_id in notification.chat_ids:
        # Дедуп до загрузки байтов: пропущенный получатель не «съедает» reuse file_id.
        claim = await idempotency_store.claim(notification.broadcast_id, chat_id)
        if claim is None:
            continue
        # первый раз — байты; дальше — уже загруженный Telegram file_id
        media = tg_file_id or BufferedInputFile(
            data, filename=f"file_{notification.file_id}"
        )
        if photo:
            result = await _send_with_retry(
                lambda media=media, chat_id=chat_id: bot.send_photo(
                    chat_id=chat_id,
                    photo=media,
                    caption=escape_html(notification.message),
                    reply_markup=reply_markup,
                ),
                chat_id,
            )
            # file_id ловим только при успешной отправке (message не None).
            message = result.message
            if message is not None and tg_file_id is None and message.photo:
                tg_file_id = message.photo[-1].file_id
        else:
            result = await _send_with_retry(
                lambda media=media, chat_id=chat_id: bot.send_document(
                    chat_id=chat_id,
                    document=media,
                    caption=escape_html(notification.message),
                    reply_markup=reply_markup,
                ),
                chat_id,
            )
            message = result.message
            if message is not None and tg_file_id is None and message.document:
                tg_file_id = message.document.file_id
        if result.status is DeliveryStatus.RETRYABLE_FAILURE:
            await idempotency_store.release(claim)
            retryable_chat_ids.append(chat_id)
        else:
            await idempotency_store.complete(claim)
        await asyncio.sleep(THROTTLE_SECONDS)

    if retryable_chat_ids:
        raise NotificationDeliveryError(
            f"temporary Telegram delivery failure for chat_ids={retryable_chat_ids}"
        )
