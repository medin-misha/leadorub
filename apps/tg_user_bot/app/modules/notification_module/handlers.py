from aiogram import Router

# Import consumer_handler to ensure RMQ listener registration side-effect executes
from .services.consumer_handler import handle_telegram_notification  # noqa: F401

router = Router(name="notification")
