"""RMQ-consumer входящих сообщений поддержки — ПЕРВЫЙ consumer backend.

Слушает очередь `telegram_support_in`, куда support_module бота публикует
сообщения пользователей, и сохраняет их в БД.

ВАЖНО про сессию БД: consumer работает вне FastAPI-запроса, поэтому привычный
`Depends(database.get_session)` недоступен. Сессию открываем фабрикой
`database.sessionmaker()` напрямую и сами управляем commit/rollback. Это
сознательное исключение из правила «только Depends» (см. backend CLAUDE.md).
"""

import logging

from app.core.database import database
from app.modules.rmq_module import RMQMessage, register_consumer

from ..schemas import SupportMessageRMQ
from .chat_service import SupportUserNotFound, store_inbound_message

logger = logging.getLogger(__name__)

SUPPORT_QUEUE = "telegram_support_in"
SUPPORT_EXCHANGE = "app.events"
SUPPORT_ROUTING_KEY = "telegram_support_in"


async def handle_support_message(message: RMQMessage) -> None:
    """Валидирует payload и сохраняет сообщение пользователя в chat_message.

    - Неизвестный telegram_id (SupportUserNotFound) → лог + ack (сообщение
      дропается, без requeue-петли): consumer не реджектит, т.к. мы не бросаем.
    - Любая другая ошибка → пробрасываем: RMQConsumerService сделает
      reject(requeue=False) и сообщение тоже дропнется (без зацикливания).
    """
    data = SupportMessageRMQ.model_validate(message.payload)
    async with database.sessionmaker() as session:
        try:
            await store_inbound_message(data, session)
            await session.commit()
        except SupportUserNotFound:
            await session.rollback()
            logger.warning(
                "[chat] support message from unknown telegram_id=%s dropped",
                data.telegram_id,
            )
        except Exception:
            await session.rollback()
            raise


# Регистрация consumer'а как side-effect импорта модуля (см. chat_module/__init__).
register_consumer(
    queue_name=SUPPORT_QUEUE,
    exchange_name=SUPPORT_EXCHANGE,
    routing_key=SUPPORT_ROUTING_KEY,
    handler=handle_support_message,
)
