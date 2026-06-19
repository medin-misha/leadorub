from logging import getLogger

from app.modules.rmq_module import RMQMessage, register_consumer

logger = getLogger(__name__)

TEST_QUEUE = "test.rmq.ping"
TEST_EXCHANGE = "app.events"
TEST_ROUTING_KEY = "test.rmq.ping"


async def handle_test_ping(message: RMQMessage) -> None:
    logger.info(
        "[test_rmq] received: event=%s message_id=%s source=%s payload=%s",
        message.event,
        message.message_id,
        message.source,
        message.payload,
    )


register_consumer(
    queue_name=TEST_QUEUE,
    exchange_name=TEST_EXCHANGE,
    routing_key=TEST_ROUTING_KEY,
    handler=handle_test_ping,
)
