from .models import ChatMessage

# Импорт регистрирует RMQ-consumer входящих сообщений поддержки как side-effect.
from .services import consumer_handler  # noqa: F401

__all__ = ["ChatMessage"]
