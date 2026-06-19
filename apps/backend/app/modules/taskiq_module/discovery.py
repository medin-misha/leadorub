import importlib
import importlib.util
import pkgutil
from logging import getLogger

import app.modules as modules_pkg

logger = getLogger(__name__)


def discover_module_tasks() -> list[str]:
    """Импортирует tasks.py из каждого модуля под app/modules/.

    Сам импорт — и есть регистрация: декораторы @taskiq_broker.task внутри
    tasks.py при импорте добавляют таски в broker. Благодаря этому новый модуль
    достаточно снабдить файлом tasks.py — инфраструктуру трогать не нужно.

    Идемпотентно: повторные вызовы не дублируют работу, так как Python кэширует
    уже импортированные модули в sys.modules.
    """
    imported: list[str] = []
    for info in pkgutil.iter_modules(modules_pkg.__path__):
        module_name = f"{modules_pkg.__name__}.{info.name}.tasks"
        if importlib.util.find_spec(module_name) is None:
            continue
        importlib.import_module(module_name)
        imported.append(module_name)
    logger.info("taskiq discovered task modules: %s", imported)
    return imported
