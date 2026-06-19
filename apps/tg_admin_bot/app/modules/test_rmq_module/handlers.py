from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.modules.rmq_module import rmq_publisher
from .services.consumer_handler import TEST_EXCHANGE, TEST_QUEUE, TEST_ROUTING_KEY

router = Router(name="test-rmq")


@router.message(Command("rmqping"))
async def rmq_ping_command(message: Message) -> None:
    msg = await rmq_publisher.publish(
        event="test.ping",
        payload={"text": "hello from telegram_template"},
        queue_name=TEST_QUEUE,
        exchange_name=TEST_EXCHANGE,
        routing_key=TEST_ROUTING_KEY,
    )
    await message.answer(f"Published: <code>{msg.message_id}</code>")
