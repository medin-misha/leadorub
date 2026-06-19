"""
Инфраструктурный роутер RabbitMQ-модуля.

Файл существует для соблюдения канонической структуры модулей
`telegram_template`. В V1 модуль не предоставляет пользовательских Telegram
команд и не регистрируется в bot runtime автоматически.
"""

from aiogram import Router

router = Router(name="rmq")
