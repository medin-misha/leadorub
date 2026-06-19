from logging import getLogger

from app.modules.rmq_module import RMQMessage, register_consumer
from ..schemas import TelegramNotification
from .sender import send_notification

logger = getLogger(__name__)

QUEUE_NAME = "telegram_notifications"
EXCHANGE_NAME = "app.events"
ROUTING_KEY = "telegram_notifications"


async def handle_telegram_notification(message: RMQMessage) -> None:
    """RMQ consumer callback that parses and validates incoming message payload,

    then routes it to the Telegram notification sender service.
    """
    logger.info(
        "[notification_module] Received notification task: message_id=%s source=%s",
        message.message_id,
        message.source,
    )
    # Parse payload using Pydantic schema to validate the contract
    notification = TelegramNotification.model_validate(message.payload)

    # Deliver notification to chat via aiogram Bot client
    await send_notification(notification)


# Register this handler with the shared RMQ consumer registry
register_consumer(
    queue_name=QUEUE_NAME,
    exchange_name=EXCHANGE_NAME,
    routing_key=ROUTING_KEY,
    handler=handle_telegram_notification,
)
