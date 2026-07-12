"""Бизнес-логика чата поддержки.

Направления:
- ВХОДЯЩЕЕ (пользователь → backend): `store_inbound_message` вызывается из
  RMQ-consumer и просто пишет строку `direction='user'`.
- ИСХОДЯЩЕЕ (админ → пользователь): `send_admin_reply` атомарно пишет строку
  `direction='admin'` и outbox-событие для очереди `telegram_notifications`.
- Чтение: `list_conversations` (список диалогов + непрочитанные),
  `get_messages` (тред), `mark_read` (сброс непрочитанных).
"""

import logging

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import and_, desc, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.file_module.models import File
from app.modules.file_module.schemas import FileCreate
from app.modules.file_module.services import s3_client
from app.modules.file_module.utils import sanitize_filename
from app.modules.rmq_module import enqueue_outbox_message
from app.modules.system import CRUD
from app.modules.telegram_module.models import TelegramUser

from ..models import ChatMessage
from ..schemas import ChatMessageCreate, ConversationRead, SupportMessageRMQ

logger = logging.getLogger(__name__)

# Контракт очереди уведомлений (admin → user). Должен совпадать с newsletter
# на backend и с consumer'ом notification_module в боте.
NOTIFICATION_EVENT = "telegram.notification"
NOTIFICATION_QUEUE = "telegram_notifications"
NOTIFICATION_EXCHANGE = "app.events"
NOTIFICATION_EXCHANGE_TYPE = "direct"


class SupportUserNotFound(Exception):
    """Сообщение поддержки пришло от неизвестного backend telegram_id.

    В consumer трактуется как «дропнуть и заacked'ить» (а не реджектить с
    requeue), чтобы не зацикливать заведомо неразрешимое сообщение.
    """

    def __init__(self, telegram_id: int) -> None:
        super().__init__(f"telegram_id={telegram_id} not found")
        self.telegram_id = telegram_id


async def _resolve_user_id(session: AsyncSession, telegram_id: int) -> int:
    """telegram_id (Telegram) → внутренний telegramuser.id (PK)."""
    stmt = select(TelegramUser.id).where(TelegramUser.telegram_id == telegram_id)
    user_id = (await session.execute(stmt)).scalar_one_or_none()
    if user_id is None:
        raise SupportUserNotFound(telegram_id)
    return user_id


async def _store_file(session: AsyncSession, file: UploadFile) -> File:
    """Заливает вложение в S3 и создаёт запись File. При сбое БД чистит S3."""
    filename = sanitize_filename(file.filename)
    link = await s3_client.create(
        file_obj=file.file,
        filename=filename,
        content_type=file.content_type or "application/octet-stream",
    )
    try:
        return await CRUD.create(
            FileCreate(link=link, name=filename, note=None), File, session
        )
    except Exception:
        await s3_client.delete(link)
        raise


async def store_inbound_message(
    data: SupportMessageRMQ, session: AsyncSession
) -> ChatMessage:
    """Сохраняет входящее ТЕКСТОВОЕ сообщение пользователя (direction='user')."""
    user_id = await _resolve_user_id(session, data.telegram_id)
    return await CRUD.create(
        ChatMessageCreate(
            telegram_user_id=user_id,
            direction="user",
            text=data.text,
            tg_message_id=data.tg_message_id,
            is_read=False,
        ),
        ChatMessage,
        session,
    )


async def store_inbound_media(
    session: AsyncSession,
    *,
    telegram_id: int,
    file: UploadFile,
    caption: str | None = None,
    tg_message_id: int | None = None,
) -> ChatMessage:
    """Сохраняет входящее МЕДИА пользователя (direction='user', file_id).

    Бот скачивает файл из Telegram и присылает его сюда multipart'ом (бинарь
    через RMQ не гоняем). Пользователя резолвим ДО заливки в S3, чтобы не
    плодить осиротевшие файлы для неизвестного telegram_id.
    """
    user_id = await _resolve_user_id(session, telegram_id)
    file_record = await _store_file(session, file)
    message = await CRUD.create(
        ChatMessageCreate(
            telegram_user_id=user_id,
            direction="user",
            text=caption,
            tg_message_id=tg_message_id,
            file_id=file_record.id,
            is_read=False,
        ),
        ChatMessage,
        session,
    )
    # Привязываем загруженный File к relationship, чтобы сериализация file_name
    # не уходила в ленивую (async-небезопасную) подгрузку.
    message.file = file_record
    return message


async def send_admin_reply(
    session: AsyncSession,
    telegram_user_id: int,
    *,
    text: str | None = None,
    file: UploadFile | None = None,
) -> ChatMessage:
    """Ответ администратора: пишет строку 'admin' и публикует сообщение боту.

    Поддерживает текст и/или вложение. Доставку файла берёт на себя существующий
    notification_module бота: он сам скачает файл по `file_id` из бэкенда и
    отправит фото/документ.

    Сообщение и outbox-событие создаются в одной DB-транзакции. Publisher увидит
    событие только после commit и безопасно повторит доставку при сбое RabbitMQ.
    """
    # telegram_id нужен, чтобы бот знал, кому слать сообщение.
    telegram_id = (
        await session.execute(
            select(TelegramUser.telegram_id).where(TelegramUser.id == telegram_user_id)
        )
    ).scalar_one_or_none()
    if telegram_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"TelegramUser with id={telegram_user_id} not found.",
        )

    file_record = await _store_file(session, file) if file is not None else None

    message = await CRUD.create(
        ChatMessageCreate(
            telegram_user_id=telegram_user_id,
            direction="admin",
            text=text,
            file_id=file_record.id if file_record else None,
        ),
        ChatMessage,
        session,
    )
    if file_record is not None:
        # См. store_inbound_media: связываем File заранее во избежание ленивой
        # подгрузки при сериализации.
        message.file = file_record

    # Переиспользуем очередь уведомлений: одно сообщение одному получателю.
    payload: dict = {"chat_ids": [telegram_id], "message": text}
    if file_record is not None:
        payload["file_id"] = file_record.id
    await enqueue_outbox_message(
        session,
        event=NOTIFICATION_EVENT,
        payload=payload,
        queue_name=NOTIFICATION_QUEUE,
        routing_key=NOTIFICATION_QUEUE,
        exchange_name=NOTIFICATION_EXCHANGE,
        exchange_type=NOTIFICATION_EXCHANGE_TYPE,
    )

    return message


async def get_messages(
    session: AsyncSession,
    telegram_user_id: int,
    *,
    after_id: int | None = None,
    limit: int = 50,
) -> list[ChatMessage]:
    """Сообщения треда в хронологическом порядке (старые → новые).

    - Первичная загрузка (`after_id` is None): последние `limit` сообщений.
    - Инкрементальный polling (`after_id` задан): только новые сообщения с
      `id > after_id` — дёшево и без повторной выгрузки всего треда.
    """
    base = select(ChatMessage).where(ChatMessage.telegram_user_id == telegram_user_id)

    if after_id is not None:
        stmt = base.where(ChatMessage.id > after_id).order_by(ChatMessage.id.asc())
        result = await session.execute(stmt.limit(limit))
        return list(result.scalars().all())

    # Берём последние N по убыванию id, затем разворачиваем в хронологию.
    result = await session.execute(base.order_by(ChatMessage.id.desc()).limit(limit))
    rows = list(result.scalars().all())
    rows.reverse()
    return rows


async def list_conversations(
    session: AsyncSession,
    *,
    search: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> list[ConversationRead]:
    """Список диалогов с превью последнего сообщения и счётчиком непрочитанных.

    Считается одним запросом: подзапрос-агрегат (max времени + count непрочитанных
    через FILTER), join к пользователю и два коррелированных скаляр-подзапроса на
    текст и направление последнего сообщения.
    """
    agg = (
        select(
            ChatMessage.telegram_user_id.label("uid"),
            func.max(ChatMessage.created_at).label("last_at"),
            func.count()
            .filter(
                and_(
                    ChatMessage.direction == "user",
                    ChatMessage.is_read.is_(False),
                )
            )
            .label("unread"),
        )
        .group_by(ChatMessage.telegram_user_id)
        .subquery()
    )

    # Текст и направление последнего сообщения диалога (коррелируют по agg.c.uid).
    last_text = (
        select(ChatMessage.text)
        .where(ChatMessage.telegram_user_id == agg.c.uid)
        .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
        .limit(1)
        .scalar_subquery()
    )
    last_direction = (
        select(ChatMessage.direction)
        .where(ChatMessage.telegram_user_id == agg.c.uid)
        .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
        .limit(1)
        .scalar_subquery()
    )

    stmt = (
        select(
            TelegramUser.id.label("telegram_user_id"),
            TelegramUser.telegram_id.label("telegram_id"),
            TelegramUser.username.label("username"),
            TelegramUser.first_name.label("first_name"),
            TelegramUser.last_name.label("last_name"),
            agg.c.last_at.label("last_at"),
            agg.c.unread.label("unread_count"),
            last_text.label("last_text"),
            last_direction.label("last_direction"),
        )
        .join(agg, agg.c.uid == TelegramUser.id)
        .order_by(desc(agg.c.last_at))
    )

    if search and search.strip():
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                TelegramUser.username.ilike(like),
                TelegramUser.first_name.ilike(like),
                TelegramUser.last_name.ilike(like),
            )
        )

    stmt = stmt.limit(limit).offset((max(page, 1) - 1) * limit)
    result = await session.execute(stmt)
    return [ConversationRead(**row._mapping) for row in result.all()]


async def mark_read(session: AsyncSession, telegram_user_id: int) -> int:
    """Помечает прочитанными все сообщения пользователя в диалоге. Возвращает кол-во."""
    stmt = (
        update(ChatMessage)
        .where(
            ChatMessage.telegram_user_id == telegram_user_id,
            ChatMessage.direction == "user",
            ChatMessage.is_read.is_(False),
        )
        .values(is_read=True)
    )
    result = await session.execute(stmt)
    return result.rowcount or 0
