# Notification Module (Telegram Client)

`notification_module` — клиентский модуль-потребитель для приёма и физической доставки уведомлений в Telegram из RabbitMQ в приложении `telegram_template`.

Этот модуль слушает очередь RabbitMQ и отправляет сообщения в Telegram с помощью `aiogram.Bot`.

## Принцип работы

1. Модуль подписывается на очередь `telegram_notifications` в обменнике `app.events` с ключом маршрутизации `telegram_notifications`.
2. При поступлении сообщения запускается callback-функция `handle_telegram_notification`.
3. Содержимое сообщения валидируется на соответствие контракту с помощью Pydantic-модели `TelegramNotification`.
4. Собирается соответствующая клавиатура (inline или reply) с учётом параметров кнопок.
5. Сообщение отправляется пользователю с помощью метода `Bot.send_message`.

## Контракт сообщения

Входящие сообщения из RMQ должны соответствовать следующей структуре:
- `chat_id` (int | str): ID чата получателя.
- `message` (str): Текст сообщения.
- `inline_buttons` (bool | None): Использовать ли inline-кнопки.
- `reply_buttons` (bool | None): Использовать ли reply-кнопки.
- `buttons` (list[list[dict]] | None): Двумерный массив с описанием кнопок:
  - `text` (str): Текст кнопки.
  - `requests_contect` (bool | None): Запрос контакта (с поддержкой опечатки из требований).
  - `request_location` (bool | None): Запрос локации.
  - `web_app` (str | None): URL Web App.

## Подключение в приложении

Модуль подключается автоматически при регистрации его роутера в реестре `app/bot/registry.py`:

```python
from app.modules.notification_module.handlers import router as notification_router

def register_routers(dispatcher: Dispatcher) -> None:
    # ...
    dispatcher.include_router(notification_router)
```

Импорт роутера активирует импорт обработчика очередей, который регистрирует консьюмер в RMQ-клиенте на этапе инициализации приложения.
