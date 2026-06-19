from datetime import datetime, timezone

from .broker import broker


@broker.task
async def send_reminder(message: str) -> None:
    """Встроенная демо-таска: образец того, как модуль объявляет свои таски.

    Любой фича-модуль создаёт рядом tasks.py и декорирует функции через
    `from app.modules.taskiq_module import taskiq_broker` + `@taskiq_broker.task`.
    """
    print(f"[{datetime.now(timezone.utc):%H:%M:%S} UTC] REMINDER: {message}")
