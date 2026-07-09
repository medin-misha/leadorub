"""
Явный реестр модульных роутеров.

Все активные Telegram-модули подключаются здесь вручную, чтобы состав
приложения был прозрачен и легко отслеживался при отладке и развитии шаблона.
"""

from aiogram import Dispatcher

from app.modules.rmq_module.handlers import router as rmq_router
from app.modules.system.handlers import router as system_router
from app.modules.requisition_module.handlers import router as requisition_router

try:
    from app.modules.notification_module.handlers import router as notification_router
except ImportError:
    notification_router = None

try:
    from app.modules.support_module.handlers import router as support_router
except ImportError:
    support_router = None


def register_routers(dispatcher: Dispatcher) -> None:
    """Подключает активные модульные роутеры к общему dispatcher."""

    # Порядок важен: system подключается первым, чтобы /start (который сбрасывает
    # режим поддержки) имел приоритет над catch-all хендлером support.
    dispatcher.include_router(system_router)
    dispatcher.include_router(rmq_router)
    if notification_router is not None:
        dispatcher.include_router(notification_router)
    if support_router is not None:
        dispatcher.include_router(support_router)
    dispatcher.include_router(requisition_router)
