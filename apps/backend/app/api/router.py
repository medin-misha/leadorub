from fastapi import APIRouter

from app.core import settings
from app.modules.system.handlers import router as system_router
from app.modules.rmq_module.handlers import router as rmq_router
from app.modules.file_module.handlers import router as file_router
from app.modules.admin_module.handlers import router as admin_router
from app.modules.taskiq_module.config import taskiq_settings
from app.modules.taskiq_module.handlers import router as taskiq_router
from app.modules.telegram_module.handlers import router as tg_router

try:
    from app.modules.telegram_notification_module.handlers import (
        router as tg_notif_router,
    )
except ImportError:
    tg_notif_router = None

router = APIRouter(prefix="/api")

# Built-in infrastructure and feature routers live here.
router.include_router(system_router)
router.include_router(rmq_router)
router.include_router(file_router)

# auth / администраторы
router.include_router(admin_router)

# taskiq debug router is opt-in: only wired when debug mode and the dedicated
# flag are enabled, mirroring the rmq debug endpoints policy.
if taskiq_settings.debug and taskiq_settings.debug_endpoints_enabled:
    router.include_router(taskiq_router)

# telegram modules
router.include_router(tg_router)

# telegram notification test router is registered if debug is True and the router is available
if settings.debug and tg_notif_router is not None:
    router.include_router(tg_notif_router)
