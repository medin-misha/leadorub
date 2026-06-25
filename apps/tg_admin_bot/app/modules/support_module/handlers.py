"""Хендлеры режима поддержки (чат пользователя с админом от имени бота).

Поток:
- `/support` → вход в FSM-состояние active, показ интро + кнопки выхода.
- текстовое сообщение в active → публикация в RMQ-очередь `telegram_support_in`
  и реакция 👀 СТРОГО после успешной публикации.
- фото/документ в active → бот скачивает файл и POST-ит на backend
  (`/api/chat/inbound-media`), затем реакция 👀 после успешной загрузки.
- `/stop` или инлайн-кнопка → выход из режима.

ВАЖНО про порядок регистрации (aiogram резолвит хендлеры по порядку внутри
роутера): команды/кнопка выхода объявлены ДО контентных обработчиков, текст/фото/
документ — до общего fallback'а; все контентные ограничены `StateFilter(active)`,
чтобы вне режима поддержки бот вёл себя как обычно. `/start` перехватывает
system-роутер (подключён раньше) и сам сбрасывает состояние.
"""

import logging
from io import BytesIO

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReactionTypeEmoji

from app.modules.rmq_module import rmq_publisher
from app.modules.system.auth import login_required

from .keyboards import EXIT_CALLBACK, support_exit_keyboard
from .services import upload_inbound_media
from .states import SupportStates

logger = logging.getLogger(__name__)

router = Router(name="support")

# Контракт очереди входящих ТЕКСТОВЫХ сообщений поддержки (бот → backend consumer).
# Должен совпадать с chat_module.consumer_handler на backend.
SUPPORT_EVENT = "telegram.support_message"
SUPPORT_QUEUE = "telegram_support_in"
SUPPORT_EXCHANGE = "app.events"
SUPPORT_EXCHANGE_TYPE = "direct"

SEEN_EMOJI = "👀"
# «Небольшие» медиа: предел размера вложения.
MAX_MEDIA_BYTES = 10 * 1024 * 1024  # 10 МБ

_INTRO = (
    "Вы в режиме поддержки. Напишите сообщение или пришлите фото/документ — "
    "мы передадим его команде.\n"
    "Доставленное сообщение мы помечаем 👀.\n\n"
    "Чтобы выйти — нажмите кнопку ниже или отправьте /stop."
)
_EXIT = "Режим поддержки завершён. Спасибо за обращение!"
_FAIL = "Не удалось доставить сообщение, попробуйте позже."
_TOO_BIG = "Файл слишком большой — до 10 МБ."
_UNSUPPORTED = "Поддерживаются только текст, фото и документы."


@router.message(Command("support"))
@login_required
async def support_start(message: Message, state: FSMContext) -> None:
    """Вход в режим поддержки. login_required гарантирует, что пользователь
    провижинен в backend (иначе consumer не сможет привязать сообщение)."""
    await state.set_state(SupportStates.active)
    await message.answer(_INTRO, reply_markup=support_exit_keyboard())


@router.message(Command("stop"), StateFilter(SupportStates.active))
async def support_stop(message: Message, state: FSMContext) -> None:
    """Выход из режима поддержки по команде /stop."""
    await state.clear()
    await message.answer(_EXIT)


@router.callback_query(F.data == EXIT_CALLBACK, StateFilter(SupportStates.active))
async def support_stop_callback(query: CallbackQuery, state: FSMContext) -> None:
    """Выход из режима поддержки по инлайн-кнопке."""
    await state.clear()
    await query.answer()
    if query.message is not None:
        await query.message.answer(_EXIT)


@router.message(StateFilter(SupportStates.active), F.text)
async def support_message(message: Message) -> None:
    """Пересылает текст пользователя в backend и ставит 👀 после публикации."""
    if message.from_user is None:
        return

    payload = {
        "telegram_id": message.from_user.id,
        "text": message.text,
        "tg_message_id": message.message_id,
    }
    try:
        await rmq_publisher.publish(
            event=SUPPORT_EVENT,
            payload=payload,
            queue_name=SUPPORT_QUEUE,
            routing_key=SUPPORT_QUEUE,
            exchange_name=SUPPORT_EXCHANGE,
            exchange_type=SUPPORT_EXCHANGE_TYPE,
        )
    except Exception:
        logger.exception("[support] failed to publish support message")
        await message.answer(_FAIL)
        return

    # 👀 = «принято в очередь». Ставим строго после успешной публикации.
    await message.react([ReactionTypeEmoji(emoji=SEEN_EMOJI)])


@router.message(StateFilter(SupportStates.active), F.photo)
async def support_photo(message: Message) -> None:
    """Пересылает фото (берём самый крупный размер)."""
    if message.from_user is None:
        return
    photo = message.photo[-1]
    await _forward_media(
        message,
        downloadable=photo,
        filename=f"photo_{message.message_id}.jpg",
        content_type="image/jpeg",
        size=photo.file_size,
    )


@router.message(StateFilter(SupportStates.active), F.document)
async def support_document(message: Message) -> None:
    """Пересылает документ (сохраняем оригинальные имя и mime)."""
    if message.from_user is None:
        return
    doc = message.document
    await _forward_media(
        message,
        downloadable=doc,
        filename=doc.file_name or f"document_{message.message_id}",
        content_type=doc.mime_type or "application/octet-stream",
        size=doc.file_size,
    )


@router.message(StateFilter(SupportStates.active))
async def support_unsupported(message: Message) -> None:
    """Прочие типы (видео/голос/стикеры) в V1 не поддерживаются."""
    await message.answer(_UNSUPPORTED)


async def _forward_media(
    message: Message,
    *,
    downloadable,
    filename: str,
    content_type: str,
    size: int | None,
) -> None:
    """Скачивает вложение из Telegram, грузит на backend, ставит 👀 при успехе.

    Размер проверяем дважды: по метаданным (до скачивания) и по факту (после).
    👀 для медиа = «сохранено на backend» (загрузка идёт по HTTP, не через RMQ).
    """
    if size is not None and size > MAX_MEDIA_BYTES:
        await message.answer(_TOO_BIG)
        return

    try:
        buffer = await message.bot.download(downloadable)
    except Exception:
        logger.exception("[support] failed to download media from Telegram")
        await message.answer(_FAIL)
        return

    data = buffer.getvalue() if isinstance(buffer, BytesIO) else buffer
    if len(data) > MAX_MEDIA_BYTES:
        await message.answer(_TOO_BIG)
        return

    try:
        await upload_inbound_media(
            telegram_id=message.from_user.id,
            data=data,
            filename=filename,
            content_type=content_type,
            caption=message.caption,
            tg_message_id=message.message_id,
        )
    except Exception:
        logger.exception("[support] failed to upload media to backend")
        await message.answer(_FAIL)
        return

    await message.react([ReactionTypeEmoji(emoji=SEEN_EMOJI)])
