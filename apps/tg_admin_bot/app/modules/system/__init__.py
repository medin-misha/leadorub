"""
Системный модуль Telegram-шаблона.

Этот пакет содержит обязательный infrastructure layer для всех остальных
Telegram-модулей: системные команды, backend client, базовую auth-логику и
process-level runtime hooks.
"""

from .handlers import router

__all__ = ["router"]
