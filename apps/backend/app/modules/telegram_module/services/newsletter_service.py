from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.system import CRUD
from app.modules.rmq_module import enqueue_outbox_message
from app.modules.file_module.models import File
from app.modules.file_module.schemas import FileCreate
from app.modules.file_module.services import s3_client
from app.modules.file_module.utils import sanitize_filename

from ..models import TelegramUser
from ..schemas import NewsletterRequest
from ..utils.limits import MESSAGE_MAX_LENGTH
from ..utils.newsletter import build_newsletter_payload

# Контракт очереди бота (см. spec). Должны совпадать с consumer_handler в tg_user_bot.
NEWSLETTER_EVENT = "telegram.newsletter"
NEWSLETTER_QUEUE = "telegram_notifications"
NEWSLETTER_EXCHANGE = "app.events"
NEWSLETTER_EXCHANGE_TYPE = "direct"


async def send_newsletter(
    request: NewsletterRequest,
    file: UploadFile | None,
    session: AsyncSession,
) -> dict:
    """Готовит и публикует рассылку ОДНИМ сообщением со списком chat_ids.

    Шаги: контент-валидация → подсчёт получателей (0 → 404) → загрузка файла →
    выборка telegram_id → публикация в RMQ.
    """
    # 1. Пустую рассылку запрещаем: нужен текст или файл.
    if not (request.text and request.text.strip()) and file is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Newsletter must contain text or a file",
        )

    # Длину ограничиваем лимитом Telegram (см. limits.py): иначе при наличии файла
    # текст-подпись > 1024 уронит отправку у бота молча. Явно отдаём 400.
    if request.text and len(request.text) > MESSAGE_MAX_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Text must not exceed {MESSAGE_MAX_LENGTH} characters",
        )

    # 2. Сначала проверяем, что под фильтр есть получатели — иначе не льём файл.
    recipients = await CRUD.count(
        model=TelegramUser,
        session=session,
        search=request.filters.search,
        field=request.filters.field,
    )
    if recipients == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No recipients match the filter",
        )

    # 3. Загружаем файл (если есть) — переиспользуем file_module.
    file_id: int | None = None
    if file is not None:
        filename = sanitize_filename(file.filename)
        link = await s3_client.create(
            file_obj=file.file,
            filename=filename,
            content_type=file.content_type or "application/octet-stream",
        )
        try:
            record = await CRUD.create(
                data=FileCreate(link=link, name=filename, note=None),
                model=File,
                session=session,
            )
        except Exception:
            await s3_client.delete(link)
            raise
        file_id = record.id

    # 4. Список chat_ids всех получателей под тем же фильтром.
    chat_ids = await CRUD.get_column(
        model=TelegramUser,
        session=session,
        column=TelegramUser.telegram_id,
        search=request.filters.search,
        field=request.filters.field,
    )

    # 5. Один broadcast_id на всю рассылку — общий ключ дедупа для всех чанков.
    broadcast_id = str(uuid4())

    # Режем аудиторию на чанки: одно RMQ-сообщение = один чанк. Это ограничивает
    # окно неакнутого сообщения (иначе длинная рассылка > consumer_timeout RMQ
    # → редоставка → дубль всей аудитории) и радиус повторных отправок при краше.
    chunk_size = settings.newsletter_chunk_size
    chunks = [chat_ids[i : i + chunk_size] for i in range(0, len(chat_ids), chunk_size)]
    chunk_total = len(chunks)

    for chunk_index, chunk in enumerate(chunks):
        payload = build_newsletter_payload(
            chat_ids=chunk,
            request=request,
            file_id=file_id,
            broadcast_id=broadcast_id,
            chunk_index=chunk_index,
            chunk_total=chunk_total,
        )
        await enqueue_outbox_message(
            session,
            event=NEWSLETTER_EVENT,
            payload=payload,
            queue_name=NEWSLETTER_QUEUE,
            routing_key=NEWSLETTER_QUEUE,
            exchange_name=NEWSLETTER_EXCHANGE,
            exchange_type=NEWSLETTER_EXCHANGE_TYPE,
        )

    return {"status": "queued", "recipients": recipients, "broadcast_id": broadcast_id}
