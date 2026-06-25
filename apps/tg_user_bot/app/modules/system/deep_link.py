"""
Разбор deep-link payload команды /start.

Telegram превращает переход по ссылке `t.me/<bot>?start=<payload>` в обычное
сообщение `/start <payload>`, где payload ограничен символами `A-Za-z0-9_-`
(до 64 символов, точка недопустима). Этот модуль отвечает только за извлечение
маркетингового `source` из payload по префиксной схеме `source_<value>`.

Схема префиксов оставляет задел на другие типы payload в будущем (например
`ref_<id>` для рефералов): для них достаточно добавить рядом отдельный парсер,
не трогая существующую логику source.
"""

from __future__ import annotations

# Префикс deep-link payload, помечающий источник трафика.
# При необходимости позже можно вынести в SystemModuleSettings.
SOURCE_PREFIX = "source_"

# Лимит колонки UserStats.source на стороне backend (String(255)).
_SOURCE_MAX_LENGTH = 255


def parse_source(args: str | None) -> str | None:
    """Извлекает source из deep-link payload вида `source_<value>`.

    Возвращает значение без префикса (например `instagram` для
    `source_instagram`) либо None, если payload пустой, не соответствует
    префиксу или хвост после префикса пустой.
    """

    if not args or not args.startswith(SOURCE_PREFIX):
        return None

    # Срезаем префикс и страхуемся от случайных пробелов в хвосте.
    value = args[len(SOURCE_PREFIX) :].strip()

    # Жёстко режем под лимит колонки, чтобы backend гарантированно принял payload.
    value = value[:_SOURCE_MAX_LENGTH]

    return value or None
