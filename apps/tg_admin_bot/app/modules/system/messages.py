"""
Загрузка текстовых шаблонов системного модуля.

Файл инкапсулирует чтение `messages.json`, чтобы хендлеры и декораторы
использовали единый источник текстов и не дублировали код чтения ресурсов.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def get_messages() -> dict[str, str]:
    """Читает и кеширует системные текстовые шаблоны."""

    messages_path = Path(__file__).with_name("messages.json")
    return json.loads(messages_path.read_text(encoding="utf-8"))
