import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.rmq_module import rmq_publisher
from app.modules.system import CRUD
from app.modules.telegram_module.models import TelegramUser

from ..models import Requisition
from ..schemas import RequisitionCreate, RequisitionStatusUpdate

if TYPE_CHECKING:
    from app.modules.telegram_module.models.telegram_user import TelegramUser

logger = logging.getLogger(__name__)

# Настройки RabbitMQ для уведомлений
NOTIFICATION_EVENT = "telegram.notification"
NOTIFICATION_QUEUE = "telegram_notifications"
NOTIFICATION_EXCHANGE = "app.events"
NOTIFICATION_EXCHANGE_TYPE = "direct"

# Настройки RabbitMQ для отправки новых заявок в будущий admin_bot
ADMIN_REQ_EVENT = "requisition.created"
ADMIN_REQ_QUEUE = "admin_requisitions"
ADMIN_REQ_EXCHANGE = "app.events"
ADMIN_REQ_EXCHANGE_TYPE = "direct"


async def create_requisition(
    data: RequisitionCreate,
    session: AsyncSession,
) -> Requisition:
    """Создаёт новую заявку от имени пользователя Telegram.

    1. Проверяет существование пользователя Telegram в БД.
    2. Сохраняет заявку со статусом 'pending' и произвольным payload.
    3. Отправляет событие в RabbitMQ для последующей обработки в admin_bot.
    """
    # 1. Поиск пользователя по telegram_id
    stmt = select(TelegramUser).where(TelegramUser.telegram_id == data.telegram_id)
    result = await session.execute(stmt)
    user = result.scalars().first()

    if not user:
        logger.warning(
            "Попытка подать заявку для несуществующего пользователя telegram_id=%s",
            data.telegram_id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Telegram user with telegram_id={data.telegram_id} not found.",
        )

    # 2. Создание заявки в БД
    requisition = Requisition(
        telegram_user_id=user.id,
        type=data.type,
        payload=data.payload,
        status="pending",
    )
    session.add(requisition)
    await session.flush()
    await session.refresh(requisition)

    # Убеждаемся, что отношение с пользователем подгружено
    requisition.telegram_user = user

    # 3. Публикация сообщения в RabbitMQ для будущего admin_bot
    created_at_val = requisition.created_at or datetime.now(timezone.utc)
    event_payload = {
        "requisition_id": requisition.id,
        "telegram_id": user.telegram_id,
        "username": user.username,
        "type": requisition.type,
        "payload": requisition.payload,
        "created_at": created_at_val.isoformat(),
    }

    try:
        await rmq_publisher.publish(
            event=ADMIN_REQ_EVENT,
            payload=event_payload,
            queue_name=ADMIN_REQ_QUEUE,
            routing_key=ADMIN_REQ_QUEUE,
            exchange_name=ADMIN_REQ_EXCHANGE,
            exchange_type=ADMIN_REQ_EXCHANGE_TYPE,
        )
        logger.info(
            "Опубликовано сообщение о новой заявке id=%s в RabbitMQ",
            requisition.id,
        )
    except Exception as exc:
        # Ошибка публикации прерывает транзакцию, чтобы избежать рассинхронизации
        logger.error(
            "Ошибка публикации новой заявки id=%s в RabbitMQ: %s",
            requisition.id,
            exc,
        )
        raise

    # Если заявка пришла из Mini App, отправляем мгновенное уведомление в бот
    if data.payload.get("source") == "miniapp":
        type_ru = {
            "consultation": "Консультация",
            "community": "Вступление в сообщество",
        }.get(requisition.type, requisition.type)
        
        user_msg = f"🎉 Ваша заявка на '{type_ru}' успешно отправлена и ожидает рассмотрения!"
        
        notification_payload = {
            "chat_ids": [user.telegram_id],
            "message": user_msg,
            "use_buttons": None,
            "buttons": None,
            "file_id": None,
        }
        
        try:
            await rmq_publisher.publish(
                event=NOTIFICATION_EVENT,
                payload=notification_payload,
                queue_name=NOTIFICATION_QUEUE,
                routing_key=NOTIFICATION_QUEUE,
                exchange_name=NOTIFICATION_EXCHANGE,
                exchange_type=NOTIFICATION_EXCHANGE_TYPE,
            )
            logger.info(
                "Опубликовано уведомление пользователю telegram_id=%s о создании заявки из Mini App",
                user.telegram_id,
            )
        except Exception as exc:
            # Ошибка отправки уведомления пользователю не должна ломать создание заявки
            logger.warning(
                "Не удалось отправить уведомление о создании заявки id=%s: %s",
                requisition.id,
                exc,
            )

    return requisition


async def list_requisitions(
    session: AsyncSession,
    *,
    status_filter: str | None = None,
    type_filter: str | None = None,
    page: int = 1,
    limit: int = 10,
    search: str | None = None,
) -> list[Requisition]:
    """Получает список заявок с пагинацией и фильтрами по статусу и типу.

    Сортировка производится по убыванию даты создания (новые заявки вверху).
    """
    stmt = select(Requisition)

    if status_filter:
        stmt = stmt.where(Requisition.status == status_filter)
    if type_filter:
        stmt = stmt.where(Requisition.type == type_filter)

    if search:
        # Применяем системный поиск по текстовым колонкам/выбранной колонке
        stmt = CRUD._apply_search(stmt, Requisition, search, None)

    # Сортировка: новые сверху
    stmt = stmt.order_by(Requisition.created_at.desc())
    stmt = stmt.limit(limit).offset((page - 1) * limit)

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def update_requisition_status(
    requisition_id: int,
    data: RequisitionStatusUpdate,
    session: AsyncSession,
) -> Requisition:
    """Обновляет статус заявки и комментарий администратора.

    После успешного сохранения отправляет уведомление пользователю в продукт-бот
    через RabbitMQ очередь 'telegram_notifications'.
    """
    # 1. Получение заявки (CRUD.get кидает 404 при отсутствии)
    requisition = await CRUD.get(model=Requisition, session=session, id=requisition_id)

    # 2. Обновление полей
    requisition.status = data.status
    requisition.admin_comment = data.admin_comment

    await session.flush()
    await session.refresh(requisition)

    # 3. Формирование сообщения об изменении статуса
    status_ru = {
        "approved": "одобрена",
        "rejected": "отклонена",
        "in_progress": "в обработке",
        "pending": "ожидает рассмотрения",
    }.get(data.status, data.status)

    type_ru = {
        "consultation": "Консультация",
        "community": "Вступление в сообщество",
    }.get(requisition.type, requisition.type)

    msg_text = f"Статус вашей заявки '{type_ru}' изменился на: *{status_ru}*."
    if data.admin_comment:
        msg_text += f"\n\nКомментарий администратора:\n{data.admin_comment}"

    # Публикация уведомления в RabbitMQ для продукт-бота
    telegram_id = requisition.telegram_user.telegram_id
    notification_payload = {
        "chat_ids": [telegram_id],
        "message": msg_text,
        "use_buttons": None,
        "buttons": None,
        "file_id": None,
    }

    try:
        await rmq_publisher.publish(
            event=NOTIFICATION_EVENT,
            payload=notification_payload,
            queue_name=NOTIFICATION_QUEUE,
            routing_key=NOTIFICATION_QUEUE,
            exchange_name=NOTIFICATION_EXCHANGE,
            exchange_type=NOTIFICATION_EXCHANGE_TYPE,
        )
        logger.info(
            "Опубликовано уведомление пользователю telegram_id=%s об изменении статуса заявки id=%s",
            telegram_id,
            requisition.id,
        )
    except Exception as exc:
        logger.error(
            "Ошибка публикации уведомления об изменении статуса заявки id=%s: %s",
            requisition.id,
            exc,
        )
        raise

    return requisition
